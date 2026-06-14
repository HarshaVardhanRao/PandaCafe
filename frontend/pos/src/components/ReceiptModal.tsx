import React, { useState, useEffect } from "react";
import api from "../api";

interface ReceiptModalProps {
  orderId: string;
  onClose: () => void;
}

export default function ReceiptModal({ orderId, onClose }: ReceiptModalProps) {
  const [order, setOrder] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [shareMethod, setShareMethod] = useState<"email" | "whatsapp" | "sms">("email");
  const [destination, setDestination] = useState("");
  const [shareStatus, setShareStatus] = useState<{ type: "success" | "error"; message: string } | null>(null);
  const [sharing, setSharing] = useState(false);

  useEffect(() => {
    const fetchOrder = async () => {
      try {
        const response = await api.get(`/orders/${orderId}`);
        setOrder(response.data);
      } catch (e) {
        console.error("Error fetching order for receipt:", e);
      } finally {
        setLoading(false);
      }
    };
    fetchOrder();
  }, [orderId]);

  const handleShare = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!destination) {
      setShareStatus({ type: "error", message: "Please enter a destination (email/phone)." });
      return;
    }

    setSharing(true);
    setShareStatus(null);

    try {
      const response = await api.post(`/orders/${orderId}/share`, {
        method: shareMethod,
        destination: destination,
      });

      setShareStatus({
        type: "success",
        message: response.data.message || `Successfully shared receipt via ${shareMethod}!`,
      });

      // If WhatsApp, open the wa.me redirection link in a new tab
      if (shareMethod === "whatsapp" && response.data.whatsapp_link) {
        window.open(response.data.whatsapp_link, "_blank");
      }
    } catch (err: any) {
      setShareStatus({
        type: "error",
        message: err.response?.data?.detail || `Failed to share receipt via ${shareMethod}.`,
      });
    } finally {
      setSharing(false);
    }
  };

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50">
        <div className="text-center">
          <svg className="animate-spin h-8 w-8 text-emerald-500 mx-auto mb-4" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          <p className="text-gray-300">Retrieving Receipt Details...</p>
        </div>
      </div>
    );
  }

  if (!order) {
    return (
      <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50">
        <div className="bg-[#111827] p-6 rounded-xl text-center max-w-sm">
          <p className="text-red-400 mb-4 font-medium">Receipt Details Not Found</p>
          <button onClick={onClose} className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg">
            Close Panel
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center p-4 z-50 overflow-y-auto">
      <div className="w-full max-w-3xl flex flex-col md:flex-row gap-6 glass-panel p-6 rounded-2xl shadow-2xl max-h-[95vh] md:max-h-none overflow-y-auto md:overflow-visible">
        
        {/* Left Side: Simulated Thermal Receipt */}
        <div className="flex-1 bg-white text-gray-900 p-6 rounded-xl font-mono shadow-md border border-gray-200 flex flex-col justify-between max-w-md mx-auto w-full">
          <div>
            <div className="text-center border-b border-dashed border-gray-300 pb-4">
              <h2 className="text-lg font-bold">🐼 PANDA CAFE 🐼</h2>
              <p className="text-xs text-gray-500">POS Billing Terminal</p>
              <p className="text-xs text-gray-500">123 Bamboo Lane, Jungle City</p>
            </div>

            <div className="py-4 text-xs space-y-1 border-b border-dashed border-gray-300">
              <div className="flex justify-between">
                <span>Receipt Number:</span>
                <span className="font-bold">{order.order_number}</span>
              </div>
              <div className="flex justify-between">
                <span>Date:</span>
                <span>{new Date(order.created_at).toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span>Order Type:</span>
                <span className="capitalize">{order.order_type.replace("_", " ")}</span>
              </div>
              {order.table && (
                <div className="flex justify-between">
                  <span>Table Number:</span>
                  <span>{order.table.table_number}</span>
                </div>
              )}
              {order.customer && (
                <div className="flex justify-between">
                  <span>Customer Name:</span>
                  <span>{order.customer.name}</span>
                </div>
              )}
            </div>

            {/* Cart Items */}
            <div className="py-4 border-b border-dashed border-gray-300">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="pb-1 font-bold">Item Description</th>
                    <th className="pb-1 text-center font-bold">Qty</th>
                    <th className="pb-1 text-right font-bold">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {order.items.map((item: any) => (
                    <tr key={item.id} className="align-top">
                      <td className="py-1">
                        <div>{item.product?.name || "Unknown Item"}</div>
                        {item.special_notes && (
                          <div className="text-[10px] text-gray-500 italic ml-2">* {item.special_notes}</div>
                        )}
                      </td>
                      <td className="py-1 text-center">{item.quantity}</td>
                      <td className="py-1 text-right">${parseFloat(item.item_total).toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Billing totals */}
            <div className="py-4 text-xs space-y-1.5 border-b border-dashed border-gray-300">
              <div className="flex justify-between">
                <span>Subtotal:</span>
                <span>${parseFloat(order.subtotal).toFixed(2)}</span>
              </div>
              <div className="flex justify-between">
                <span>Tax:</span>
                <span>${parseFloat(order.tax_amount).toFixed(2)}</span>
              </div>
              {parseFloat(order.discount_amount) > 0 && (
                <div className="flex justify-between text-red-600 font-medium">
                  <span>Discount Applied:</span>
                  <span>-${parseFloat(order.discount_amount).toFixed(2)}</span>
                </div>
              )}
              <div className="flex justify-between text-sm font-bold pt-1">
                <span>TOTAL AMOUNT:</span>
                <span>${parseFloat(order.total_amount).toFixed(2)}</span>
              </div>
            </div>

            {/* Payments detail */}
            {order.payments && order.payments.length > 0 && (
              <div className="py-4 text-xs space-y-1">
                <div className="font-bold pb-1 text-gray-600">Payments Processed:</div>
                {order.payments.map((p: any) => (
                  <div key={p.id} className="flex justify-between text-gray-500">
                    <span className="capitalize">{p.payment_method} Payment</span>
                    <span>${parseFloat(p.amount).toFixed(2)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="text-center pt-4 border-t border-dashed border-gray-300">
            <p className="text-[11px] text-gray-600 font-bold">Thank you for visiting Panda Cafe!</p>
            <p className="text-[9px] text-gray-400">Powered by PandaPOS 1.0</p>
          </div>
        </div>

        {/* Right Side: Simulated Share Form */}
        <div className="flex-1 flex flex-col justify-between max-w-sm mx-auto w-full">
          <div>
            <h3 className="text-xl font-bold text-white mb-2">Simulate Receipt Sharing</h3>
            <p className="text-gray-400 text-sm mb-6">
              Simulate invoice delivery to the customer. Output logs will be stored in text files in the backend.
            </p>

            {shareStatus && (
              <div
                className={`p-3 rounded-lg text-sm text-center mb-4 ${
                  shareStatus.type === "success"
                    ? "bg-emerald-950/50 border border-emerald-500/50 text-emerald-300"
                    : "bg-red-950/50 border border-red-500/50 text-red-300"
                }`}
              >
                {shareStatus.message}
              </div>
            )}

            <form onSubmit={handleShare} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Select Share Method</label>
                <div className="grid grid-cols-3 gap-2">
                  {(["email", "whatsapp", "sms"] as const).map((method) => (
                    <button
                      key={method}
                      type="button"
                      onClick={() => {
                        setShareMethod(method);
                        setDestination(method === "email" ? "customer@example.com" : "+91-9999988888");
                        setShareStatus(null);
                      }}
                      className={`py-2 px-3 text-xs font-semibold rounded-lg border capitalize transition-all ${
                        shareMethod === method
                          ? "bg-emerald-600/20 border-emerald-500 text-emerald-300"
                          : "bg-[#111827] border-gray-800 text-gray-400 hover:border-gray-700"
                      }`}
                    >
                      {method}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  {shareMethod === "email" ? "Email Address" : "Phone Number (with country code)"}
                </label>
                <input
                  type={shareMethod === "email" ? "email" : "text"}
                  value={destination}
                  onChange={(e) => setDestination(e.target.value)}
                  placeholder={shareMethod === "email" ? "customer@example.com" : "+91-9999988888"}
                  className="w-full px-4 py-3 bg-[#111827] border border-gray-800 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 text-white placeholder-gray-600 transition-all text-sm"
                />
              </div>

              <button
                type="submit"
                disabled={sharing}
                className="w-full py-3 bg-emerald-600 hover:bg-emerald-500 disabled:bg-emerald-800 disabled:cursor-not-allowed text-white font-medium rounded-xl transition-all shadow-lg shadow-emerald-900/20 text-sm"
              >
                {sharing ? "Sending Simulation..." : `Share via ${shareMethod.toUpperCase()}`}
              </button>
            </form>
          </div>

          <button
            onClick={onClose}
            className="w-full mt-8 py-3 bg-gray-800 hover:bg-gray-700 text-white font-medium rounded-xl transition-all border border-gray-700 text-sm"
          >
            Return to Terminal
          </button>
        </div>

      </div>
    </div>
  );
}
