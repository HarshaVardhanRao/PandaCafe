import React, { useState } from "react";
import api from "../api";

interface CheckoutDrawerProps {
  orderId: string;
  totalAmount: number;
  onPaymentSuccess: () => void;
  onClose: () => void;
}

interface SplitItem {
  payment_method: string;
  amount: number;
  reference_number?: string;
}

export default function CheckoutDrawer({
  orderId,
  totalAmount,
  onPaymentSuccess,
  onClose,
}: CheckoutDrawerProps) {
  const [isSplit, setIsSplit] = useState(false);
  const [paymentMethod, setPaymentMethod] = useState("cash");
  const [reference, setReference] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Split states
  const [splits, setSplits] = useState<SplitItem[]>([]);
  const [splitMethod, setSplitMethod] = useState("cash");
  const [splitAmount, setSplitAmount] = useState<number>(0);
  const [splitReference, setSplitReference] = useState("");

  const getSplitSum = () => splits.reduce((sum, item) => sum + item.amount, 0);
  const remainingSplit = totalAmount - getSplitSum();

  const handleSinglePayment = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      // 1. Process payment
      await api.post(`/orders/${orderId}/payments`, {
        amount: totalAmount,
        payment_method: paymentMethod,
        reference_number: reference || undefined,
      });

      // 2. Complete order (sets status to completed, triggering loyalty logic)
      await api.patch(`/orders/${orderId}/complete`);

      onPaymentSuccess();
    } catch (err: any) {
      setError(
        err.response?.data?.detail || "Error processing single payment transaction."
      );
    } finally {
      setLoading(false);
    }
  };

  const handleAddSplit = () => {
    if (splitAmount <= 0) {
      setError("Split amount must be greater than 0.");
      return;
    }
    if (splitAmount > remainingSplit) {
      setError(`Split amount exceeds remaining unpaid balance of $${remainingSplit.toFixed(2)}.`);
      return;
    }

    setSplits([
      ...splits,
      {
        payment_method: splitMethod,
        amount: splitAmount,
        reference_number: splitReference || undefined,
      },
    ]);

    setSplitAmount(0);
    setSplitReference("");
    setError(null);
  };

  const handleRemoveSplit = (index: number) => {
    setSplits(splits.filter((_, i) => i !== index));
    setError(null);
  };

  const handleSplitPayment = async () => {
    if (Math.abs(remainingSplit) > 0.01) {
      setError(`Split totals must sum up exactly to the total amount of $${totalAmount.toFixed(2)}.`);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // 1. Process split payments
      await api.post(`/orders/${orderId}/split-payment`, paymentsPayload(splits));

      // 2. Complete order
      await api.patch(`/orders/${orderId}/complete`);

      onPaymentSuccess();
    } catch (err: any) {
      setError(
        err.response?.data?.detail || "Error processing split payments transaction."
      );
    } finally {
      setLoading(false);
    }
  };

  // Convert schema fields correctly
  const paymentsPayload = (items: SplitItem[]) => {
    return items.map((item) => ({
      amount: item.amount,
      payment_method: item.payment_method,
      reference_number: item.reference_number,
    }));
  };

  return (
    <div className="fixed inset-y-0 right-0 w-full max-w-md bg-[#0F172A] border-l border-gray-800 shadow-2xl z-50 flex flex-col justify-between">
      {/* Header */}
      <div className="p-6 border-b border-gray-800 flex justify-between items-center bg-[#1E293B]/40">
        <div>
          <h2 className="text-xl font-bold text-white">Select Payment</h2>
          <p className="text-gray-400 text-xs mt-1">Invoice Amount: ${totalAmount.toFixed(2)}</p>
        </div>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-white bg-gray-800/50 hover:bg-gray-800 p-2 rounded-lg transition-all"
        >
          ✕
        </button>
      </div>

      {/* Main Form Area */}
      <div className="flex-1 p-6 overflow-y-auto space-y-6">
        {error && (
          <div className="bg-red-950/50 border border-red-500/50 text-red-300 p-3 rounded-lg text-sm text-center">
            ⚠️ {error}
          </div>
        )}

        {/* Payment Type Selection */}
        <div className="flex bg-[#1E293B]/50 p-1.5 rounded-xl border border-gray-800">
          <button
            onClick={() => {
              setIsSplit(false);
              setError(null);
            }}
            className={`flex-1 py-2 text-xs font-semibold rounded-lg transition-all ${
              !isSplit ? "bg-emerald-600 text-white shadow-md" : "text-gray-400 hover:text-white"
            }`}
          >
            Single Method
          </button>
          <button
            onClick={() => {
              setIsSplit(true);
              setError(null);
            }}
            className={`flex-1 py-2 text-xs font-semibold rounded-lg transition-all ${
              isSplit ? "bg-emerald-600 text-white shadow-md" : "text-gray-400 hover:text-white"
            }`}
          >
            Split Invoice
          </button>
        </div>

        {/* Render Single Payment */}
        {!isSplit ? (
          <form onSubmit={handleSinglePayment} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Payment Option</label>
              <div className="grid grid-cols-3 gap-2">
                {["cash", "card", "upi"].map((method) => (
                  <button
                    key={method}
                    type="button"
                    onClick={() => setPaymentMethod(method)}
                    className={`py-3 px-4 text-xs font-semibold rounded-xl border capitalize transition-all ${
                      paymentMethod === method
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
              <label className="block text-sm font-medium text-gray-300 mb-2">Reference / Tx ID (Optional)</label>
              <input
                type="text"
                value={reference}
                onChange={(e) => setReference(e.target.value)}
                placeholder="e.g. Card Auth Code / UPI Ref ID"
                className="w-full px-4 py-3 bg-[#111827] border border-gray-800 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 text-white placeholder-gray-600 transition-all text-sm"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-emerald-600 hover:bg-emerald-500 disabled:bg-emerald-800 disabled:cursor-not-allowed text-white font-medium rounded-xl transition-all shadow-lg shadow-emerald-900/20 text-sm mt-6"
            >
              {loading ? "Completing payment..." : `Process Payment - $${totalAmount.toFixed(2)}`}
            </button>
          </form>
        ) : (
          /* Render Split Payment */
          <div className="space-y-4">
            {/* Added Splits List */}
            {splits.length > 0 && (
              <div className="space-y-2 border border-gray-800 bg-[#111827] rounded-xl p-3">
                <p className="text-gray-400 text-xs font-semibold">Payment Breakdowns:</p>
                {splits.map((item, idx) => (
                  <div key={idx} className="flex justify-between items-center text-xs bg-[#1E293B]/40 py-2 px-3 rounded-lg">
                    <span className="capitalize text-white font-medium">
                      {item.payment_method}
                      {item.reference_number && <span className="text-[10px] text-gray-500 block font-normal">Ref: {item.reference_number}</span>}
                    </span>
                    <div className="flex items-center gap-2">
                      <span className="text-emerald-400 font-bold">${item.amount.toFixed(2)}</span>
                      <button
                        onClick={() => handleRemoveSplit(idx)}
                        className="text-red-400 hover:text-red-300 p-1 font-bold text-[11px]"
                      >
                        ✕
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Split Builder Form */}
            {remainingSplit > 0 && (
              <div className="border border-gray-800 bg-[#1E293B]/20 rounded-xl p-4 space-y-3">
                <p className="text-gray-300 text-xs font-semibold">Add Split Amount</p>
                <div className="grid grid-cols-3 gap-2">
                  {["cash", "card", "upi"].map((method) => (
                    <button
                      key={method}
                      type="button"
                      onClick={() => setSplitMethod(method)}
                      className={`py-2 px-3 text-[11px] font-semibold rounded-lg border capitalize transition-all ${
                        splitMethod === method
                          ? "bg-emerald-600/25 border-emerald-500 text-emerald-300"
                          : "bg-[#111827] border-gray-800 text-gray-400 hover:border-gray-700"
                      }`}
                    >
                      {method}
                    </button>
                  ))}
                </div>

                <div className="flex gap-2">
                  <div className="flex-1">
                    <input
                      type="number"
                      value={splitAmount || ""}
                      onChange={(e) => setSplitAmount(parseFloat(e.target.value) || 0)}
                      placeholder="Amount"
                      className="w-full px-3 py-2 bg-[#111827] border border-gray-800 rounded-lg focus:outline-none focus:ring-1 focus:ring-emerald-500/50 focus:border-emerald-500 text-white placeholder-gray-600 text-xs"
                    />
                  </div>
                  <button
                    onClick={() => setSplitAmount(remainingSplit)}
                    className="px-2 bg-gray-800 hover:bg-gray-700 text-gray-300 text-[10px] rounded-lg border border-gray-700"
                  >
                    Max
                  </button>
                </div>

                <input
                  type="text"
                  value={splitReference}
                  onChange={(e) => setSplitReference(e.target.value)}
                  placeholder="Reference Code (Optional)"
                  className="w-full px-3 py-2 bg-[#111827] border border-gray-800 rounded-lg focus:outline-none focus:ring-1 focus:ring-emerald-500/50 focus:border-emerald-500 text-white placeholder-gray-600 text-xs"
                />

                <button
                  onClick={handleAddSplit}
                  className="w-full py-2 bg-[#1E293B] hover:bg-gray-700 text-emerald-400 hover:text-emerald-300 text-xs font-semibold rounded-lg border border-gray-800"
                >
                  + Add Split
                </button>
              </div>
            )}

            {/* Split Details summary */}
            <div className="flex justify-between items-center text-xs py-2 px-3 border border-gray-800 bg-[#111827] rounded-xl font-semibold">
              <span className="text-gray-400">Remaining Balance:</span>
              <span className={remainingSplit > 0 ? "text-amber-400" : "text-emerald-400"}>
                ${remainingSplit.toFixed(2)}
              </span>
            </div>

            <button
              onClick={handleSplitPayment}
              disabled={loading || remainingSplit > 0.01}
              className="w-full py-3 bg-emerald-600 hover:bg-emerald-500 disabled:bg-emerald-800 disabled:cursor-not-allowed text-white font-medium rounded-xl transition-all shadow-lg shadow-emerald-900/20 text-sm mt-6"
            >
              {loading ? "Completing payment..." : `Process Splits - $${totalAmount.toFixed(2)}`}
            </button>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-6 border-t border-gray-800 bg-[#1E293B]/40 text-center">
        <button
          onClick={onClose}
          className="w-full py-3 bg-gray-800 hover:bg-gray-700 text-white font-medium rounded-xl border border-gray-700 text-sm transition-all"
        >
          Cancel Checkout
        </button>
      </div>
    </div>
  );
}
