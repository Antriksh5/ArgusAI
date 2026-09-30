import { useEffect, useState, useRef } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { Camera, AlertTriangle, Eye, ShieldAlert, Video, Search, RefreshCw, XCircle, PlaySquare } from 'lucide-react';

// Types
type Location = { latitude: number; longitude: number };
type VehicleEvent = {
  id: number;
  camera_id: string;
  source_video: string;
  is_simulated_reuse: boolean;
  plate_text: string;
  confidence: number;
  location: Location;
  timestamp: string;
  is_watchlist_match: boolean;
};
type HazardEvent = {
  id: number;
  camera_id: string;
  source_video: string;
  is_simulated_reuse: boolean;
  class_name: string;
  confidence: number;
  verification_status: string;
  location: Location;
  timestamp: string;
};
type Trajectory = {
  plate_text: string;
  is_watchlist_match: boolean;
  is_simulated_reuse: boolean;
  is_synthetic_demo?: boolean;
  points: { camera_id: string; timestamp: string; lat: number; lon: number; confidence: number }[];
};
type Summary = {
  cameras: number;
  vehicle_events: number;
  watchlist_alerts: number;
  hazards: number;
};

// Helper: shorten camera_id for display
function camLabel(camera_id: string) {
  return camera_id.replace('cam_bus_', 'Bus ').replace(/_hyderabad_.+/, '').replace('_', ' ');
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

const carSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 17h2c.6 0 1-.4 1-1v-3c0-.9-.7-1.7-1.5-1.9C18.7 10.6 16 10 16 10s-1.3-1.4-2.2-2.3c-.5-.4-1.1-.7-1.8-.7H5c-.6 0-1.1.4-1.4.9l-1.4 2.9A3.7 3.7 0 0 0 2 12v4c0 .6.4 1 1 1h2"/><circle cx="7" cy="17" r="2"/><path d="M9 17h6"/><circle cx="17" cy="17" r="2"/></svg>`;
const warningSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>`;
const shieldSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.5 3.8 17 5 19 5a1 1 0 0 1 1 1z"/></svg>`;

function clusterHazards(hazards: HazardEvent[], radiusDeg = 0.0015) {
  const clusters: { lat: number; lon: number; items: HazardEvent[] }[] = [];
  for (const h of hazards) {
    if (!h.location) continue; // skip events with no GPS
    let placed = false;
    for (const c of clusters) {
      if (Math.abs(c.lat - h.location.latitude) < radiusDeg && Math.abs(c.lon - h.location.longitude) < radiusDeg) {
        c.items.push(h);
        placed = true;
        break;
      }
    }
    if (!placed) {
      clusters.push({ lat: h.location.latitude, lon: h.location.longitude, items: [h] });
    }
  }
  return clusters;
}

export default function App() {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const markersRef = useRef<maplibregl.Marker[]>([]);
  
  const [summary, setSummary] = useState<Summary | null>(null);
  const [vehicles, setVehicles] = useState<VehicleEvent[]>([]);
  const [hazards, setHazards] = useState<HazardEvent[]>([]);
  const [alerts, setAlerts] = useState<VehicleEvent[]>([]);
  const [trajectories, setTrajectories] = useState<Trajectory[]>([]);
  const [activeTrajectory, setActiveTrajectory] = useState<Trajectory | null>(null);
  const [search, setSearch] = useState('');
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  useEffect(() => {
    document.title = "ARGUS | Real-time Dashboard";
  }, []);

  const fetchData = async () => {
    try {
      const [sumRes, vehRes, hazRes, alertRes, trajRes] = await Promise.all([
        fetch(`${API_BASE}/api/summary`),
        fetch(`${API_BASE}/api/events`),
        fetch(`${API_BASE}/api/hazards`),
        fetch(`${API_BASE}/api/alerts`),
        fetch(`${API_BASE}/api/trajectories`)
      ]);
      
      if (!sumRes.ok || !vehRes.ok || !hazRes.ok || !alertRes.ok || !trajRes.ok) {
        throw new Error("API response not ok");
      }

      setSummary(await sumRes.json());
      setVehicles(await vehRes.json());
      setHazards(await hazRes.json());
      setAlerts(await alertRes.json());
      setTrajectories(await trajRes.json());
      setError(false);
      setLastUpdated(new Date());
    } catch (e) {
      console.error("Failed to fetch API data", e);
      setError(true);
    } finally {
      setLoading(false);
    }
  };

  const loadDemoTrajectory = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/demo/trajectory`);
      if (res.ok) {
        const data = await res.json();
        data.is_synthetic_demo = true;
        setActiveTrajectory(data);
        if (data.points[0]) flyTo({ latitude: data.points[0].lat, longitude: data.points[0].lon });
      }
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (!mapContainer.current || map.current) return;

    map.current = new maplibregl.Map({
      container: mapContainer.current,
      style: {
        version: 8,
        sources: {
          osm: {
            type: 'raster',
            tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
            tileSize: 256,
            attribution: '&copy; OpenStreetMap Contributors',
          }
        },
        layers: [{
          id: 'osm',
          type: 'raster',
          source: 'osm',
          minzoom: 0,
          maxzoom: 22
        }]
      },
      center: [78.4867, 17.3850],
      zoom: 13
    });

    map.current.on('load', () => {
      const cam1Route = [[78.4867,17.3850],[78.4880,17.3870],[78.4905,17.3892],[78.4920,17.3910],[78.4935,17.3935],[78.4950,17.3950]];
      const cam2Route = [[78.4867,17.3850],[78.4855,17.3830],[78.4840,17.3812],[78.4820,17.3795],[78.4800,17.3775],[78.4780,17.3750]];
      const cam3Route = [[78.4867,17.3850],[78.4888,17.3845],[78.4908,17.3842],[78.4928,17.3838],[78.4947,17.3835],[78.4967,17.3850]];

      map.current!.addSource('routes', {
        type: 'geojson',
        data: {
          type: 'FeatureCollection',
          features: [
            { type: 'Feature', geometry: { type: 'LineString', coordinates: cam1Route }, properties: { purpose: 'alpr' } },
            { type: 'Feature', geometry: { type: 'LineString', coordinates: cam2Route }, properties: { purpose: 'alpr' } },
            { type: 'Feature', geometry: { type: 'LineString', coordinates: cam3Route }, properties: { purpose: 'hazard' } },
          ]
        }
      });

      map.current!.addLayer({
        id: 'routes-line-alpr', type: 'line', source: 'routes', filter: ['==', ['get', 'purpose'], 'alpr'],
        layout: { 'line-join': 'round', 'line-cap': 'round' },
        paint: { 'line-color': '#1C5D8C', 'line-width': 3, 'line-opacity': 0.8 }
      });
      map.current!.addLayer({
        id: 'routes-line-hazard', type: 'line', source: 'routes', filter: ['==', ['get', 'purpose'], 'hazard'],
        layout: { 'line-join': 'round', 'line-cap': 'round' },
        paint: { 'line-color': '#C76A1E', 'line-width': 3, 'line-opacity': 0.8, 'line-dasharray': [2, 2] }
      });
    });
  }, []);

  useEffect(() => {
    if (!map.current) return;

    markersRef.current.forEach(m => m.remove());
    markersRef.current = [];

    const addHTMLMarker = (lat: number, lon: number, htmlIcon: string, colorClass: string, popupHTML: string) => {
      const el = document.createElement('div');
      // Flat style: no shadow-md, ring, or large sizes
      el.className = `w-5 h-5 rounded-full flex items-center justify-center border border-white text-white cursor-pointer ${colorClass}`;
      el.innerHTML = htmlIcon;
      const popup = new maplibregl.Popup({ offset: 12, closeButton: false }).setHTML(popupHTML);
      
      const marker = new maplibregl.Marker({ element: el })
        .setLngLat([lon, lat])
        .setPopup(popup)
        .addTo(map.current!);
      markersRef.current.push(marker);
    };

    vehicles.forEach(v => {
      if (!v.is_watchlist_match && v.location) {
        addHTMLMarker(v.location.latitude, v.location.longitude, carSvg, 'bg-[#1C5D8C]',
          `<div style="color:black;font-size:13px;font-family:Arial, sans-serif">
            <div style="font-weight:bold;margin-bottom:4px;color:#1C5D8C">Vehicle Sighting</div>
            <div style="font-family:Arial, sans-serif;font-size:14px;font-weight:bold;margin-bottom:4px">${v.plate_text}</div>
            <div>Cam: ${camLabel(v.camera_id)}</div>
            <div>Time: ${new Date(v.timestamp).toLocaleTimeString()}</div>
            <div style="width:100%;background:#e5e7eb;border-radius:2px;height:2px;margin-top:6px">
              <div style="background:#1C5D8C;height:100%;border-radius:2px;width:${v.confidence*100}%"></div>
            </div>
          </div>`
        );
      }
    });

    alerts.forEach(a => {
      if (!a.location) return;
      addHTMLMarker(a.location.latitude, a.location.longitude, shieldSvg, 'bg-red-600',
        `<div style="color:black;font-size:13px;font-family:Arial, sans-serif">
          <div style="font-weight:bold;margin-bottom:4px;color:#dc2626">Watchlist Alert</div>
          <div style="font-family:Arial, sans-serif;font-size:14px;font-weight:bold;color:#dc2626;margin-bottom:4px">${a.plate_text}</div>
          <div>Cam: ${camLabel(a.camera_id)}</div>
          <div>Time: ${new Date(a.timestamp).toLocaleTimeString()}</div>
        </div>`
      );
    });

    const hazClusters = clusterHazards(hazards);
    hazClusters.forEach(c => {
      const best = c.items.reduce((max, h) => h.confidence > max.confidence ? h : max, c.items[0]);
      const opacity = best.verification_status === 'unverified' ? 'opacity-80' : 'opacity-100';
      const label = c.items.length > 1 ? `<span style="position:absolute;top:-5px;right:-5px;background:#C76A1E;font-size:8px;font-weight:bold;padding:0px 3px;border-radius:8px;border:1px solid white">${c.items.length}</span>` : '';
      const iconHtml = warningSvg + label;
      
      let popupContent = `<div style="color:black;font-size:13px;font-family:Arial, sans-serif">
        <div style="font-weight:bold;margin-bottom:4px;color:#C76A1E">Hazard Cluster (${c.items.length})</div>
        <div>Best type: ${best.class_name}</div>
        <div>Cam: ${camLabel(best.camera_id)}</div>
        <div style="width:100%;background:#e5e7eb;border-radius:2px;height:2px;margin-top:6px">
          <div style="background:#C76A1E;height:100%;border-radius:2px;width:${best.confidence*100}%"></div>
        </div>
      </div>`;
      
      addHTMLMarker(c.lat, c.lon, iconHtml, `bg-[#C76A1E] ${opacity}`, popupContent);
    });

    const drawTraj = () => {
      if (!map.current) return;
      const coords = activeTrajectory
        ? activeTrajectory.points.filter(p => p.lon && p.lat).map(p => [p.lon, p.lat])
        : [];
      const geojson: any = {
        type: 'FeatureCollection',
        features: coords.length ? [{ type: 'Feature', geometry: { type: 'LineString', coordinates: coords }, properties: {} }] : []
      };
      
      const isDemo = activeTrajectory?.is_synthetic_demo;
      const color = isDemo ? '#ec4899' : '#1C5D8C';
      const dash = isDemo ? [4, 4] : undefined;

      if (map.current.getSource('trajectory')) {
        (map.current.getSource('trajectory') as maplibregl.GeoJSONSource).setData(geojson);
        map.current.setPaintProperty('trajectory-line', 'line-color', color);
        if (dash) {
          map.current.setPaintProperty('trajectory-line', 'line-dasharray', dash);
        } else {
          map.current.setPaintProperty('trajectory-line', 'line-dasharray', [1]); // Solid
        }
      } else {
        map.current.addSource('trajectory', { type: 'geojson', data: geojson });
        map.current.addLayer({ 
          id: 'trajectory-line', 
          type: 'line', 
          source: 'trajectory', 
          paint: { 
            'line-color': color, 
            'line-width': 3,
            'line-dasharray': dash ?? [1]
          } 
        });
      }
    };

    if (map.current.isStyleLoaded()) {
      drawTraj();
    } else {
      map.current.once('load', drawTraj);
    }

  }, [vehicles, hazards, alerts, activeTrajectory]);

  const flyTo = (loc: Location) => {
    if (map.current && loc) {
      map.current.flyTo({ center: [loc.longitude, loc.latitude], zoom: 17, duration: 1200 });
    }
  };

  const filteredHazards = hazards.filter(h => h.class_name.toLowerCase().includes(search.toLowerCase()) || camLabel(h.camera_id).toLowerCase().includes(search.toLowerCase()));
  const filteredVehicles = vehicles.filter(v => v.plate_text.toLowerCase().includes(search.toLowerCase()) || camLabel(v.camera_id).toLowerCase().includes(search.toLowerCase()));

  return (
    <div className="flex flex-col h-screen bg-[#0f172a] text-slate-200" style={{ fontFamily: 'Arial, sans-serif' }}>
      <header className="flex items-center justify-between px-6 py-4 bg-[#0f172a] border-b border-slate-800 shrink-0 z-20">
        <div className="flex items-center gap-4">
          <div className=" text-white font-black tracking-tighter text-2xl px-2 py-1 rounded">
            ARGUS
          </div>
          {error && (
            <span className="bg-red-900/50 border border-red-500/40 text-red-200 text-xs px-2.5 py-1 rounded-full flex items-center gap-1.5 animate-pulse">
              <XCircle size={12} /> Connection Error
            </span>
          )}
        </div>
        
        <div className="flex gap-8 items-center">
          {lastUpdated && (
            <div className="text-[10px] text-slate-500 flex items-center gap-1 mr-4">
              <RefreshCw size={10} className={loading ? 'animate-spin text-slate-400' : ''} />
              Updated {lastUpdated.toLocaleTimeString()}
            </div>
          )}
          {[
            { label: 'Cameras', value: summary?.cameras ?? 0, color: 'text-[#1C5D8C]', icon: <Camera size={12}/> },
            { label: 'Sightings', value: summary?.vehicle_events ?? 0, color: 'text-slate-300', icon: <Eye size={12}/> },
            { label: 'Alerts', value: summary?.watchlist_alerts ?? 0, color: 'text-red-500', icon: <ShieldAlert size={12}/> },
            { label: 'Hazards', value: summary?.hazards ?? 0, color: 'text-[#C76A1E]', icon: <AlertTriangle size={12}/> },
          ].map(({ label, value, color, icon }) => (
            <div key={label} className="flex flex-col items-center">
              <span className={`text-2xl font-bold leading-none ${color}`}>{value}</span>
              <span className="text-[10px] uppercase tracking-widest text-slate-400 flex items-center gap-1 mt-1">{icon} {label}</span>
            </div>
          ))}
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        <div className="flex-1 relative">
          <div ref={mapContainer} className="absolute inset-0" />

          {/* Legend */}
          <div className="absolute bottom-6 right-6 bg-[#0f172a]/95 backdrop-blur-md p-4 rounded border border-slate-700 text-xs z-10 shadow-lg">
            <div className="font-bold mb-3 text-slate-300 border-b border-slate-800 pb-2 tracking-wide uppercase text-[10px]">Legend</div>
            <div className="space-y-2">
              <div className="flex items-center gap-2"><div className="w-3 h-3 bg-[#1C5D8C] border border-white"/><span>Vehicle</span></div>
              <div className="flex items-center gap-2"><div className="w-3 h-3 bg-red-600 border border-white"/><span>Watchlist Alert</span></div>
              <div className="flex items-center gap-2"><div className="w-3 h-3 bg-[#C76A1E] border border-white"/><span>Hazard</span></div>
              <div className="mt-2 pt-2 border-t border-slate-800 space-y-2">
                <div className="flex items-center gap-2"><div className="w-4 h-0.5 bg-[#1C5D8C]"/><span>ALPR Route (Bus 01, 02)</span></div>
                <div className="flex items-center gap-2"><div className="w-4 h-0.5 border-b-2 border-dashed border-[#C76A1E]"/><span>Hazard Route (Bus 03)</span></div>
              </div>
            </div>
          </div>

          {activeTrajectory && (
            <div className="absolute top-6 left-1/2 -translate-x-1/2 bg-[#0f172a]/95 border border-slate-700 text-slate-200 text-sm px-4 py-2 rounded backdrop-blur z-10 flex items-center gap-2 shadow-lg">
              <ShieldAlert size={16} className={activeTrajectory.is_watchlist_match ? "text-red-500" : "text-[#1C5D8C]"}/> 
              Trajectory: <b className="font-sans tracking-wide">{activeTrajectory.plate_text}</b>
              <button onClick={() => setActiveTrajectory(null)} className="ml-2 text-slate-400 hover:text-white transition-colors"><XCircle size={14}/></button>
            </div>
          )}

          {activeTrajectory?.is_synthetic_demo && (
            <div className="absolute bottom-6 left-1/2 -translate-x-1/2 bg-yellow-900/95 border border-yellow-500 text-yellow-100 text-xs px-4 py-2 rounded font-bold uppercase tracking-widest z-10 shadow-lg">
              SYNTHETIC DEMO DATA - ILLUSTRATIVE ONLY
            </div>
          )}
        </div>

        <div className="w-[380px] bg-[#0f172a] border-l border-slate-800 overflow-y-auto flex flex-col z-10">
          <div className="p-4 border-b border-slate-800 sticky top-0 bg-[#0f172a]/95 backdrop-blur z-10">
            <div className="relative">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input 
                type="text" 
                placeholder="Filter plates or cameras..." 
                className="w-full bg-[#1e293b] border border-slate-700 rounded py-1.5 pl-9 pr-3 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-[#1C5D8C] transition-colors"
                value={search}
                onChange={e => setSearch(e.target.value)}
              />
            </div>
          </div>

          <div className="p-4 flex flex-col gap-6">
            <section>
              <h2 className="text-red-500 font-bold uppercase tracking-widest text-[10px] flex items-center gap-2 mb-3">
                <ShieldAlert size={12}/> Watchlist Alerts
              </h2>
              {loading && alerts.length === 0 ? <div className="text-slate-500 text-xs italic">Loading...</div> :
               alerts.length === 0 ? <div className="text-slate-500 text-xs italic bg-[#1e293b] p-3 rounded text-center">No alerts.</div> :
               alerts.map(a => (
                <div key={a.id}
                  className="bg-[#1e293b] p-3 rounded mb-2 cursor-pointer hover:bg-slate-800 border-l-2 border-red-600 transition-colors group"
                  onClick={() => {
                    flyTo(a.location);
                    setActiveTrajectory(trajectories.find(t => t.plate_text === a.plate_text) ?? null);
                  }}>
                  <div className="flex justify-between items-start mb-1">
                    <div className="font-sans text-slate-200 font-bold text-base tracking-wide">{a.plate_text}</div>
                  </div>
                  <div className="text-xs text-slate-400 flex justify-between items-center mt-2">
                    <span className="truncate">{camLabel(a.camera_id)}</span>
                    <span>{new Date(a.timestamp).toLocaleTimeString()}</span>
                  </div>
                </div>
              ))}
            </section>

            <section>
              <h2 className="text-[#1C5D8C] font-bold uppercase tracking-widest text-[10px] flex items-center gap-2 mb-3">
                <Eye size={12}/> Cross-Camera Trajectories
              </h2>
              {trajectories.map(t => (
                <div key={t.plate_text}
                  className="bg-[#1e293b] p-3 rounded mb-2 cursor-pointer hover:bg-slate-800 border-l-2 border-[#1C5D8C] transition-colors"
                  onClick={() => {
                    setActiveTrajectory(t);
                    if (t.points[0]) flyTo({ latitude: t.points[0].lat, longitude: t.points[0].lon });
                  }}>
                  <div className="font-sans text-slate-200 font-bold tracking-wide">{t.plate_text}</div>
                  <div className="text-xs text-slate-400 mt-1">{t.points.length} sightings across {new Set(t.points.map(p => p.camera_id)).size} cameras</div>
                </div>
              ))}
              
              <button 
                onClick={loadDemoTrajectory}
                className="w-full mt-2 bg-[#1e293b] text-slate-300 text-[10px] uppercase font-bold py-2 px-3 rounded border border-slate-700 hover:bg-slate-700 transition-colors flex items-center justify-center gap-2"
              >
                <PlaySquare size={12} className="text-pink-500" />
                Show Demo: Cross-Camera Trajectory (Synthetic Example)
              </button>
            </section>

            <section>
              <h2 className="text-[#C76A1E] font-bold uppercase tracking-widest text-[10px] flex items-center justify-between mb-3">
                <span className="flex items-center gap-2"><AlertTriangle size={12}/> Recent Hazards</span>
                <span className="text-slate-500 lowercase tracking-normal">{filteredHazards.length} total</span>
              </h2>
              {loading && hazards.length === 0 ? <div className="text-slate-500 text-xs italic">Loading...</div> :
               hazards.length === 0 ? <div className="text-slate-500 text-xs italic bg-[#1e293b] p-3 rounded text-center">No hazards.</div> :
               filteredHazards.map(h => (
                <div key={h.id}
                  className="bg-[#1e293b] p-3 rounded mb-2 cursor-pointer hover:bg-slate-800 border-l-2 border-[#C76A1E] transition-colors"
                  onClick={() => flyTo(h.location)}>
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-slate-200 font-semibold text-sm">{h.class_name}</span>
                  </div>
                  
                  <div className="text-[11px] text-slate-400 flex justify-between items-center mt-2">
                    <span className="truncate pr-2">{camLabel(h.camera_id)}</span>
                    <span>{new Date(h.timestamp).toLocaleTimeString()}</span>
                  </div>
                  <div className="mt-2 flex items-center gap-2">
                    <div className="flex-1 bg-[#0f172a] h-0.5 rounded-full overflow-hidden">
                      <div className="bg-[#C76A1E] h-full rounded-full" style={{width: `${h.confidence * 100}%`}}></div>
                    </div>
                  </div>
                </div>
              ))}
            </section>

            <section>
              <h2 className="text-[#1C5D8C] font-bold uppercase tracking-widest text-[10px] flex items-center gap-2 mb-3">
                <Eye size={12}/> Vehicle Sightings
              </h2>
              {loading && vehicles.length === 0 ? <div className="text-slate-500 text-xs italic">Loading...</div> :
               vehicles.length === 0 ? <div className="text-slate-500 text-xs italic bg-[#1e293b] p-3 rounded text-center">No sightings.</div> :
               filteredVehicles.map(v => (
                <div key={v.id} className="bg-[#1e293b] p-3 rounded mb-2 cursor-pointer hover:bg-slate-800 border-l-2 border-[#1C5D8C] transition-colors" onClick={() => flyTo(v.location)}>
                  <div className="flex justify-between items-start mb-1">
                    <div className="font-sans text-slate-200 font-bold tracking-wide">{v.plate_text}</div>
                  </div>
                  <div className="text-[11px] text-slate-400 flex justify-between items-center mt-2">
                    <span className="truncate pr-2">{camLabel(v.camera_id)}</span>
                    <span>{new Date(v.timestamp).toLocaleTimeString()}</span>
                  </div>
                  <div className="mt-2 flex items-center gap-2">
                    <div className="flex-1 bg-[#0f172a] h-0.5 rounded-full overflow-hidden">
                      <div className="bg-[#1C5D8C] h-full rounded-full" style={{width: `${v.confidence * 100}%`}}></div>
                    </div>
                  </div>
                </div>
              ))
            }
            </section>
          </div>
        </div>
      </div>
    </div>
  );
}
