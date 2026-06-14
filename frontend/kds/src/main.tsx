import React, { useEffect, useState, useRef } from "react";
import ReactDOM from "react-dom/client";
import "./index.css";

// Configure API and WS hosts
const BACKEND_HOST = window.location.hostname ? `${window.location.hostname}:8000` : "localhost:8000";
const API_URL = `http://${BACKEND_HOST}/api/v1`;
const WS_URL = `ws://${BACKEND_HOST}/api/v1/ws/kds`;

interface OrderItem {
  id: string;
  product_name: string;
  quantity: number;
  special_notes: string;
}

interface KDSOrder {
  id: string;
  order_number: string;
  order_type: string;
  table_number: number | null;
  status: string; // pending, accepted, preparing, ready
  notes: string;
  created_at: string;
  items: OrderItem[];
}

function KDSApp() {
  const [orders, setOrders] = useState<KDSOrder[]>([]);
  const [wsConnected, setWsConnected] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectIntervalRef = useRef<number | null>(null);
  const [playNotification, setPlayNotification] = useState<boolean>(false);

  // Fetch initial active orders
  const fetchActiveOrders = async () => {
    try {
      const response = await fetch(`${API_URL}/kds/orders`);
      if (!response.ok) {
        throw new Error("Failed to fetch active kitchen orders");
      }
      const data = await response.json();
      setOrders(data);
      setError(null);
    } catch (err: any) {
      setError(err.message || "Network error fetching orders");
    }
  };

  // Sound generator using Web Audio API (so we don't need external audio files)
  const beep = () => {
    try {
      const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "sine";
      osc.frequency.setValueAtTime(587.33, ctx.currentTime); // D5 note
      osc.connect(gain);
      gain.connect(ctx.destination);
      gain.gain.setValueAtTime(0.1, ctx.currentTime);
      osc.start();
      osc.stop(ctx.currentTime + 0.15);
      
      setTimeout(() => {
        const osc2 = ctx.createOscillator();
        const gain2 = ctx.createGain();
        osc2.type = "sine";
        osc2.frequency.setValueAtTime(880.00, ctx.currentTime); // A5 note
        osc2.connect(gain2);
        gain2.connect(ctx.destination);
        gain2.gain.setValueAtTime(0.1, ctx.currentTime);
        osc2.start();
        osc2.stop(ctx.currentTime + 0.25);
      }, 150);
    } catch (e) {
      console.warn("AudioContext failed", e);
    }
  };

  // WebSocket Connection
  const connectWebSocket = () => {
    if (wsRef.current) {
      wsRef.current.close();
    }

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      setWsConnected(true);
      if (reconnectIntervalRef.current) {
        clearInterval(reconnectIntervalRef.current);
        reconnectIntervalRef.current = null;
      }
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === "order_update") {
          const updatedOrder: KDSOrder = msg.data;
          
          setOrders((prevOrders) => {
            const activeStatuses = ["pending", "accepted", "preparing", "ready"];
            
            // If order status is no longer active in KDS, remove it
            if (!activeStatuses.includes(updatedOrder.status)) {
              return prevOrders.filter((o) => o.id !== updatedOrder.id);
            }

            const exists = prevOrders.some((o) => o.id === updatedOrder.id);
            if (exists) {
              // Update existing order
              return prevOrders.map((o) => (o.id === updatedOrder.id ? updatedOrder : o));
            } else {
              // Add new order (and beep if it's new!)
              beep();
              setPlayNotification(true);
              setTimeout(() => setPlayNotification(false), 2000);
              return [...prevOrders, updatedOrder].sort((a, b) => 
                new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
              );
            }
          });
        }
      } catch (err) {
        console.error("Error parsing WebSocket message", err);
      }
    };

    ws.onclose = () => {
      setWsConnected(false);
      // Attempt reconnect every 3s
      if (!reconnectIntervalRef.current) {
        reconnectIntervalRef.current = window.setInterval(() => {
          connectWebSocket();
        }, 3000);
      }
    };

    ws.onerror = (err) => {
      console.error("KDS WS Error:", err);
      ws.close();
    };
  };

  useEffect(() => {
    fetchActiveOrders();
    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectIntervalRef.current) {
        clearInterval(reconnectIntervalRef.current);
      }
    };
  }, []);

  // Update order status via patch
  const handleUpdateStatus = async (orderId: string, nextStatus: string) => {
    try {
      const response = await fetch(`${API_URL}/kds/orders/${orderId}/status`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ status: nextStatus }),
      });
      if (!response.ok) {
        throw new Error("Failed to update status");
      }
      const updatedOrder = await response.json();
      
      // Update local state (in case WebSocket message is delayed)
      setOrders((prevOrders) => {
        const activeStatuses = ["pending", "accepted", "preparing", "ready"];
        if (!activeStatuses.includes(updatedOrder.status)) {
          return prevOrders.filter((o) => o.id !== orderId);
        }
        return prevOrders.map((o) => (o.id === orderId ? updatedOrder : o));
      });
    } catch (err: any) {
      alert(err.message || "Error updating status");
    }
  };

  // Group stats
  const pendingCount = orders.filter((o) => o.status === "pending" || o.status === "accepted").length;
  const preparingCount = orders.filter((o) => o.status === "preparing").length;
  const readyCount = orders.filter((o) => o.status === "ready").length;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans select-none antialiased">
      {/* Top Banner Alert */}
      {playNotification && (
        <div className="bg-emerald-500 text-slate-950 py-3 px-6 text-center font-bold text-lg animate-bounce shadow-lg flex items-center justify-center gap-2">
          <span>🔔</span> NEW KITCHEN ORDER RECEIVED!
        </div>
      )}

      {/* Header */}
      <header className="bg-slate-900 border-b border-slate-800 px-6 py-4 flex flex-col sm:flex-row justify-between items-center gap-4 shadow-md">
        <div className="flex items-center gap-3">
          <div className="bg-emerald-500/10 p-2 rounded-lg border border-emerald-500/20">
            <span className="text-2xl">🐼</span>
          </div>
          <div>
            <h1 className="text-xl font-extrabold tracking-tight bg-gradient-to-r from-emerald-400 to-teal-300 bg-clip-text text-transparent">
              PandaCafe KDS
            </h1>
            <p className="text-xs text-slate-400 font-medium">Kitchen Display System Dashboard</p>
          </div>
        </div>

        {/* Stats and Reconnect */}
        <div className="flex flex-wrap items-center gap-6">
          <div className="flex items-center gap-4 bg-slate-950/50 py-1.5 px-4 rounded-xl border border-slate-800/80 text-sm font-semibold">
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-500 animate-pulse"></span>
              <span className="text-slate-400">Incoming:</span>
              <span className="text-amber-400 font-mono text-base font-bold">{pendingCount}</span>
            </div>
            <div className="w-px h-4 bg-slate-800"></div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-sky-500 animate-pulse"></span>
              <span className="text-slate-400">Preparing:</span>
              <span className="text-sky-400 font-mono text-base font-bold">{preparingCount}</span>
            </div>
            <div className="w-px h-4 bg-slate-800"></div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
              <span className="text-slate-400">Ready:</span>
              <span className="text-emerald-400 font-mono text-base font-bold">{readyCount}</span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className={`w-3.5 h-3.5 rounded-full ${wsConnected ? "bg-emerald-500 shadow-emerald-500/50 shadow-sm" : "bg-rose-500 animate-ping"}`} />
            <span className="text-sm font-bold tracking-wide">
              {wsConnected ? (
                <span className="text-emerald-400">CONNECTED</span>
              ) : (
                <span className="text-rose-450">RECONNECTING...</span>
              )}
            </span>
          </div>

          <button 
            onClick={fetchActiveOrders}
            className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 active:scale-95 border border-slate-700/50 text-slate-300 hover:text-slate-100 transition-all cursor-pointer"
            title="Force refresh list"
          >
            🔄
          </button>
        </div>
      </header>

      {/* Main Grid View */}
      <main className="flex-1 overflow-y-auto p-6">
        {error && (
          <div className="max-w-xl mx-auto mb-6 bg-rose-500/10 border border-rose-500/30 rounded-2xl p-4 text-center text-rose-400 text-sm font-semibold flex items-center justify-center gap-2">
            <span>⚠️</span> {error}
          </div>
        )}

        {orders.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-96 gap-4 text-slate-500">
            <div className="text-5xl opacity-40">🍳</div>
            <p className="text-lg font-bold">No active kitchen orders</p>
            <p className="text-sm">Incoming POS orders will appear here automatically.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {orders.map((order) => (
              <OrderCard 
                key={order.id} 
                order={order} 
                onUpdateStatus={handleUpdateStatus} 
              />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

// Timer Component to show elapsed minutes/seconds
function OrderTimer({ createdAt }: { createdAt: string }) {
  const [elapsedSeconds, setElapsedSeconds] = useState<number>(0);

  useEffect(() => {
    const calculateElapsed = () => {
      const created = new Date(createdAt).getTime();
      const now = new Date().getTime();
      setElapsedSeconds(Math.max(0, Math.floor((now - created) / 1000)));
    };

    calculateElapsed();
    const interval = setInterval(calculateElapsed, 1000);
    return () => clearInterval(interval);
  }, [createdAt]);

  const mins = Math.floor(elapsedSeconds / 60);
  const secs = elapsedSeconds % 60;
  const timeString = `${mins}:${secs < 10 ? "0" : ""}${secs}`;

  // Time brackets: Green (< 5m), Orange (5m-10m), Red (> 10m)
  let badgeColor = "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20";
  if (mins >= 10) {
    badgeColor = "bg-rose-500/20 text-rose-400 border border-rose-500/30 animate-pulse font-extrabold";
  } else if (mins >= 5) {
    badgeColor = "bg-amber-500/10 text-amber-400 border border-amber-500/20 font-bold";
  }

  return (
    <div className={`px-3 py-1 rounded-xl text-sm font-mono tracking-wider ${badgeColor}`}>
      ⏱️ {timeString}
    </div>
  );
}

function OrderCard({ 
  order, 
  onUpdateStatus 
}: { 
  order: KDSOrder; 
  onUpdateStatus: (orderId: string, nextStatus: string) => void;
}) {
  const getStatusDisplay = () => {
    switch (order.status) {
      case "pending":
      case "accepted":
        return { label: "NEW ORDER", color: "bg-amber-500/20 text-amber-400 border-amber-500/30" };
      case "preparing":
        return { label: "PREPARING", color: "bg-sky-500/20 text-sky-400 border-sky-500/30" };
      case "ready":
        return { label: "READY TO SERVE", color: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30" };
      default:
        return { label: order.status.toUpperCase(), color: "bg-slate-800 text-slate-400 border-slate-700" };
    }
  };

  const statusInfo = getStatusDisplay();

  return (
    <div className="bg-slate-900 border border-slate-800/80 rounded-2xl overflow-hidden shadow-lg hover:shadow-xl transition-all duration-300 flex flex-col justify-between hover:border-slate-700">
      {/* Card Header */}
      <div className="bg-slate-900/40 p-4 border-b border-slate-850 flex justify-between items-start">
        <div>
          <span className="text-slate-400 text-xs font-mono font-bold tracking-wider">KOT TICKET</span>
          <h2 className="text-xl font-black text-slate-100 tracking-tight font-mono">{order.order_number}</h2>
          <div className="mt-1 flex items-center gap-2">
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
              {order.order_type === "dine_in" ? `🍽️ Table ${order.table_number || "N/A"}` : "🛍️ Take Away"}
            </span>
          </div>
        </div>
        <div className="flex flex-col items-end gap-1.5">
          <OrderTimer createdAt={order.created_at} />
          <span className={`text-2xs font-extrabold px-2 py-0.5 rounded-lg border ${statusInfo.color}`}>
            {statusInfo.label}
          </span>
        </div>
      </div>

      {/* Line Items */}
      <div className="p-4 flex-1 space-y-3">
        {order.items.map((item) => (
          <div key={item.id} className="pb-3 border-b border-slate-850/60 last:border-0 flex items-start gap-3">
            <div className="bg-slate-800 text-emerald-400 font-extrabold rounded-lg w-8 h-8 flex items-center justify-center text-lg font-mono flex-shrink-0 border border-slate-700/40">
              {item.quantity}
            </div>
            <div className="flex-1 min-w-0 pt-0.5">
              <p className="text-slate-100 text-md font-bold leading-tight truncate">
                {item.product_name}
              </p>
              {item.special_notes && (
                <div className="mt-1 px-2.5 py-1 rounded bg-rose-500/5 text-rose-450/90 text-xs font-bold border border-rose-500/10 inline-block">
                  ⚠️ Note: {item.special_notes}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Ticket Notes */}
      {order.notes && (
        <div className="px-4 pb-4 pt-1">
          <div className="bg-slate-950/40 border border-slate-850 rounded-xl p-2.5">
            <span className="text-slate-500 text-3xs font-extrabold block uppercase tracking-wide">Ticket Comment</span>
            <p className="text-xs text-slate-350 italic mt-0.5">{order.notes}</p>
          </div>
        </div>
      )}

      {/* Card Footer Actions */}
      <div className="bg-slate-900/60 p-4 border-t border-slate-850 flex gap-3">
        {(order.status === "pending" || order.status === "accepted") && (
          <button
            onClick={() => onUpdateStatus(order.id, "preparing")}
            className="flex-1 py-3 px-4 bg-gradient-to-r from-sky-600 to-sky-500 hover:from-sky-500 hover:to-sky-400 active:scale-[0.98] text-slate-100 rounded-xl font-bold tracking-wide transition-all shadow-md shadow-sky-950/20 text-sm cursor-pointer"
          >
            Start Preparing 🍳
          </button>
        )}
        {order.status === "preparing" && (
          <button
            onClick={() => onUpdateStatus(order.id, "ready")}
            className="flex-1 py-3 px-4 bg-gradient-to-r from-emerald-600 to-emerald-500 hover:from-emerald-500 hover:to-emerald-450 active:scale-[0.98] text-slate-100 rounded-xl font-bold tracking-wide transition-all shadow-md shadow-emerald-950/20 text-sm cursor-pointer"
          >
            Mark Ready 📦
          </button>
        )}
        {order.status === "ready" && (
          <button
            onClick={() => onUpdateStatus(order.id, "served")}
            className="flex-1 py-3 px-4 bg-gradient-to-r from-teal-600 to-teal-500 hover:from-teal-500 hover:to-teal-450 active:scale-[0.98] text-slate-100 rounded-xl font-bold tracking-wide transition-all shadow-md shadow-teal-950/20 text-sm cursor-pointer"
          >
            Serve Order ✔️
          </button>
        )}
      </div>
    </div>
  );
}

const rootElement = document.getElementById("root");
if (rootElement) {
  ReactDOM.createRoot(rootElement).render(
    <React.StrictMode>
      <KDSApp />
    </React.StrictMode>
  );
}