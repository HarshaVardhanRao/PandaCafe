import React, { useEffect, useState } from "react";
import api from "../api";
import { usePOSStore, Product, Category, Table, CartItem } from "../store";
import CheckoutDrawer from "./CheckoutDrawer";
import ReceiptModal from "./ReceiptModal";

export default function Dashboard() {
  const store = usePOSStore();
  const [loading, setLoading] = useState(true);

  // UI state
  const [activeCategory, setActiveCategory] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [itemQuantity, setItemQuantity] = useState(1);
  const [itemNotes, setItemNotes] = useState("");
  const [showCheckout, setShowCheckout] = useState(false);
  const [showReceipt, setShowReceipt] = useState<string | null>(null);

  // Loyalty states
  const [phoneQuery, setPhoneQuery] = useState("");
  const [lookupLoading, setLookupLoading] = useState(false);
  const [pointsToRedeem, setPointsToRedeem] = useState<number>(0);
  const [loyaltyMessage, setLoyaltyMessage] = useState<string | null>(null);

  // Table merging states
  const [mergeMode, setMergeMode] = useState(false);
  const [selectedMergeTables, setSelectedMergeTables] = useState<string[]>([]);

  // Fetch initial catalog and tables
  const fetchData = async () => {
    try {
      const [catsRes, prodsRes, tablesRes] = await Promise.all([
        api.get("/products/categories"),
        api.get("/products"),
        api.get("/tables"),
      ]);
      store.setCatalog(catsRes.data, prodsRes.data);
      store.setTables(tablesRes.data);
    } catch (e) {
      console.error("Error loading POS initial data:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Poll tables status every 5 seconds to keep synchronized
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const tablesRes = await api.get("/tables");
        store.setTables(tablesRes.data);
      } catch (e) {
        console.error("Error polling tables status:", e);
      }
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  // Calculate pricing totals
  const getSubtotal = () => {
    return store.cart.reduce((sum, item) => sum + item.price * item.quantity, 0);
  };
  const getTax = () => {
    return store.cart.reduce(
      (sum, item) => sum + item.price * (item.tax_percent / 100) * item.quantity,
      0
    );
  };
  const getDiscount = () => {
    return store.discount ? store.discount.amount : 0;
  };
  const getTotal = () => {
    return Math.max(0, getSubtotal() + getTax() - getDiscount());
  };

  // Add item handler
  const handleAddItem = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProduct) return;
    store.addToCart(selectedProduct, itemQuantity, itemNotes);
    setSelectedProduct(null);
    setItemQuantity(1);
    setItemNotes("");
  };

  // Customer phone lookup
  const handleCustomerLookup = async () => {
    if (!phoneQuery) return;
    setLookupLoading(true);
    setLoyaltyMessage(null);

    try {
      const res = await api.get(`/customers/lookup/${phoneQuery}`);
      store.setCustomer(res.data);
      setLoyaltyMessage(`Customer linked: ${res.data.name} (${res.data.loyalty_points} pts)`);
    } catch (err: any) {
      if (err.response?.status === 404) {
        // Option to create
        setLoyaltyMessage("Not found. Enter name to auto-register.");
      } else {
        setLoyaltyMessage("Lookup failed. Please check network connection.");
      }
    } finally {
      setLookupLoading(false);
    }
  };

  // Quick Customer Registration
  const [regName, setRegName] = useState("");
  const handleQuickRegister = async () => {
    if (!phoneQuery || !regName) return;
    setLookupLoading(true);
    try {
      const res = await api.post("/customers", {
        name: regName,
        phone_number: phoneQuery,
      });
      store.setCustomer(res.data);
      setRegName("");
      setLoyaltyMessage(`Registered & Linked: ${res.data.name}`);
    } catch (e) {
      setLoyaltyMessage("Failed to register customer.");
    } finally {
      setLookupLoading(false);
    }
  };

  // Loyalty Point Redemption
  const handleRedeemPoints = async () => {
    if (!store.customer || pointsToRedeem <= 0) return;
    if (pointsToRedeem > store.customer.loyalty_points) {
      setLoyaltyMessage(`Insufficient balance. Available: ${store.customer.loyalty_points} points.`);
      return;
    }

    // Apply points discount (1 point = 1 currency unit discount)
    // We apply discount locally and link it in the checkout invoice
    store.setDiscount({
      amount: pointsToRedeem,
      percentage: 0,
      code: "LOYALTY_REDEMPTION",
      points_redeemed: pointsToRedeem,
    });
    setLoyaltyMessage(`Applied loyalty discount of $${pointsToRedeem.toFixed(2)}!`);
    setPointsToRedeem(0);
  };

  // Handle Checkout Drawer Open
  const handleCheckoutOpen = async () => {
    if (store.cart.length === 0) return;

    setLoading(true);
    try {
      // 1. Create order in backend (sets status to pending)
      const orderData: any = {
        order_type: store.orderType,
        table_id: store.activeTable ? store.activeTable.id : undefined,
        customer_id: store.customer ? store.customer.id : undefined,
        notes: store.discount?.points_redeemed
          ? `[REDEEMED_POINTS: ${store.discount.points_redeemed}]`
          : undefined,
      };

      const orderRes = await api.post("/orders", orderData);
      const createdOrder = orderRes.data;

      // 2. Add all cart items to order in backend
      for (const item of store.cart) {
        await api.post(`/orders/${createdOrder.id}/items`, {
          product_id: item.product_id,
          quantity: item.quantity,
          special_notes: item.special_notes || undefined,
        });
      }

      // 3. Apply points discount in backend if applicable
      if (store.discount?.points_redeemed) {
        await api.post(`/orders/${createdOrder.id}/discount?discount_amount=${store.discount.amount}`);
      }

      store.setActiveOrder(createdOrder);
      setShowCheckout(true);
    } catch (e: any) {
      alert("Error initializing order in backend: " + (e.response?.data?.detail || e.message));
    } finally {
      setLoading(false);
    }
  };

  // Merge table implementation
  const handleMergeTables = async () => {
    if (selectedMergeTables.length < 2) {
      alert("Please select at least 2 tables to merge.");
      return;
    }
    try {
      await api.post("/tables/merge", { table_ids: selectedMergeTables });
      alert("Tables merged successfully!");
      setMergeMode(false);
      setSelectedMergeTables([]);
      fetchData();
    } catch (e) {
      alert("Failed to merge tables.");
    }
  };

  // Table Selection
  const handleTableSelect = async (table: Table) => {
    if (mergeMode) {
      if (selectedMergeTables.includes(table.id)) {
        setSelectedMergeTables(selectedMergeTables.filter((id) => id !== table.id));
      } else {
        setSelectedMergeTables([...selectedMergeTables, table.id]);
      }
      return;
    }

    if (table.status === "occupied" && table.current_order_id) {
      // Load existing occupied order
      setLoading(true);
      try {
        const orderRes = await api.get(`/orders/${table.current_order_id}`);
        const order = orderRes.data;
        store.loadCartFromOrder(order, order.items);
        store.setActiveTable(table);
      } catch (e) {
        console.error("Error loading occupied table order:", e);
      } finally {
        setLoading(false);
      }
    } else {
      // Start new order for table
      store.setActiveTable(table);
      store.clearCart();
    }
  };

  // Filter products
  const filteredProducts = store.products.filter((p) => {
    const matchCat = activeCategory === "all" || p.category_id === activeCategory;
    const matchSearch = p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                        p.sku.toLowerCase().includes(searchQuery.toLowerCase());
    return matchCat && matchSearch && p.is_available;
  });

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#070A13]">
        <div className="text-center">
          <svg className="animate-spin h-10 w-10 text-emerald-500 mx-auto mb-4" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          <p className="text-gray-400">Loading Cashier Dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-[#070A13]">
      {/* Header */}
      <header className="px-6 py-4 bg-[#111827]/80 border-b border-gray-800 flex justify-between items-center z-25 sticky top-0 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <span className="text-2xl">🐼</span>
          <div>
            <h1 className="text-xl font-bold text-white tracking-wide">PandaCafe</h1>
            <p className="text-[10px] text-emerald-400 font-mono tracking-wider font-semibold uppercase">Cashier Terminal</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-right">
            <span className="text-sm font-medium text-gray-300 block">{store.user?.username}</span>
            <span className="text-xs text-gray-500 capitalize">{store.user?.role}</span>
          </div>
          <button
            onClick={() => store.setToken(null)}
            className="px-4 py-2 bg-gray-850 hover:bg-red-950/30 text-gray-400 hover:text-red-400 border border-gray-800 hover:border-red-900 rounded-xl transition-all text-xs font-semibold"
          >
            Log Out
          </button>
        </div>
      </header>

      {/* Workspace Grid */}
      <div className="flex-1 flex flex-col lg:flex-row p-6 gap-6 max-h-[calc(100vh-73px)] overflow-hidden">
        
        {/* LEFT COLUMN: Table Grid & held orders (~25% width) */}
        <div className="w-full lg:w-1/4 flex flex-col gap-6 max-h-[85vh] lg:max-h-none overflow-y-auto pr-1">
          {/* Order type and merge tables */}
          <div className="glass-panel p-4 rounded-2xl flex flex-col gap-3">
            <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider">Order Configuration</h3>
            <div className="grid grid-cols-3 gap-1.5 bg-[#111827] p-1 rounded-xl border border-gray-800">
              {(["dine_in", "take_away", "delivery"] as const).map((type) => (
                <button
                  key={type}
                  onClick={() => store.setOrderType(type)}
                  className={`py-2 text-[10px] font-bold rounded-lg capitalize transition-all ${
                    store.orderType === type
                      ? "bg-emerald-600 text-white shadow-md shadow-emerald-950/20"
                      : "text-gray-400 hover:text-white"
                  }`}
                >
                  {type.replace("_", " ")}
                </button>
              ))}
            </div>

            {/* Merge Tables */}
            <div className="flex justify-between items-center mt-2 border-t border-gray-800 pt-3">
              <span className="text-xs text-gray-400">Merge Mode</span>
              <button
                onClick={() => {
                  setMergeMode(!mergeMode);
                  setSelectedMergeTables([]);
                }}
                className={`py-1 px-3 text-[10px] font-bold rounded-lg border transition-all ${
                  mergeMode
                    ? "bg-amber-600/20 border-amber-500 text-amber-300"
                    : "bg-gray-800/40 border-gray-800 text-gray-400 hover:border-gray-700"
                }`}
              >
                {mergeMode ? "Cancel" : "Enable"}
              </button>
            </div>
            {mergeMode && (
              <button
                onClick={handleMergeTables}
                className="w-full py-2 bg-amber-600 hover:bg-amber-500 text-white font-semibold rounded-lg text-xs transition-all mt-1"
              >
                Merge Selected ({selectedMergeTables.length})
              </button>
            )}
          </div>

          {/* Tables Grid */}
          <div className="glass-panel p-4 rounded-2xl flex-1 flex flex-col min-h-[250px]">
            <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">Dining Tables</h3>
            <div className="grid grid-cols-4 gap-2 overflow-y-auto pr-1">
              {store.tables.map((t) => {
                const isSelected = store.activeTable?.id === t.id;
                const isSelectedForMerge = selectedMergeTables.includes(t.id);
                
                let colorClass = "bg-emerald-950/20 border-emerald-900 text-emerald-400 hover:bg-emerald-900/10";
                if (t.status === "occupied") {
                  colorClass = "bg-red-950/20 border-red-900 text-red-400 hover:bg-red-900/10";
                } else if (t.status === "reserved") {
                  colorClass = "bg-amber-950/20 border-amber-900 text-amber-400 hover:bg-amber-900/10";
                } else if (t.status === "cleaning") {
                  colorClass = "bg-blue-950/20 border-blue-900 text-blue-400 hover:bg-blue-900/10";
                }

                if (isSelected) {
                  colorClass = "bg-emerald-600 border-emerald-500 text-white";
                } else if (isSelectedForMerge) {
                  colorClass = "bg-amber-600 border-amber-500 text-white";
                }

                return (
                  <button
                    key={t.id}
                    onClick={() => handleTableSelect(t)}
                    className={`aspect-square flex flex-col justify-center items-center rounded-xl border text-xs font-bold transition-all relative ${colorClass}`}
                  >
                    <span>T-{t.table_number}</span>
                    <span className="text-[8px] opacity-75 font-normal">Cap: {t.capacity}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Held Orders List */}
          {store.heldOrders.length > 0 && (
            <div className="glass-panel p-4 rounded-2xl max-h-[200px] flex flex-col">
              <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">Suspended Orders</h3>
              <div className="space-y-2 overflow-y-auto pr-1">
                {store.heldOrders.map((o) => (
                  <div key={o.id} className="flex justify-between items-center text-xs bg-[#111827] p-2 rounded-lg border border-gray-800">
                    <div>
                      <span className="text-white block font-semibold">{o.order_number}</span>
                      <span className="text-[10px] text-gray-500 capitalize">
                        {o.order_type.replace("_", " ")} {o.table_number ? `(T-${o.table_number})` : ""}
                      </span>
                    </div>
                    <button
                      onClick={() => store.resumeHeldOrder(o.id)}
                      className="px-2.5 py-1 bg-emerald-600/20 border border-emerald-500/50 hover:bg-emerald-600 text-emerald-400 hover:text-white text-[10px] font-bold rounded-md transition-all"
                    >
                      Resume
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* MIDDLE COLUMN: Category and Product Selection (~45% width) */}
        <div className="w-full lg:w-5/12 flex flex-col gap-4 max-h-[85vh] lg:max-h-none overflow-y-auto pr-1">
          {/* Search and Categories */}
          <div className="glass-panel p-4 rounded-2xl space-y-4">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search products by SKU or Name..."
              className="w-full px-4 py-3 bg-[#111827]/80 border border-gray-800 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 text-white placeholder-gray-650 transition-all text-sm"
            />

            <div className="flex gap-2 overflow-x-auto pb-1 max-w-full">
              <button
                onClick={() => setActiveCategory("all")}
                className={`py-1.5 px-3 text-xs font-semibold rounded-lg border whitespace-nowrap transition-all ${
                  activeCategory === "all"
                    ? "bg-emerald-600/20 border-emerald-500 text-emerald-300"
                    : "bg-[#111827] border-gray-800 text-gray-400 hover:border-gray-700"
                }`}
              >
                All Items
              </button>
              {store.categories.map((c) => (
                <button
                  key={c.id}
                  onClick={() => setActiveCategory(c.id)}
                  className={`py-1.5 px-3 text-xs font-semibold rounded-lg border whitespace-nowrap transition-all ${
                    activeCategory === c.id
                      ? "bg-emerald-600/20 border-emerald-500 text-emerald-300"
                      : "bg-[#111827] border-gray-800 text-gray-400 hover:border-gray-700"
                  }`}
                >
                  {c.name}
                </button>
              ))}
            </div>
          </div>

          {/* Product Cards Grid */}
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3 overflow-y-auto flex-1 pr-1 pb-4">
            {filteredProducts.map((p) => (
              <button
                key={p.id}
                onClick={() => setSelectedProduct(p)}
                className="glass-card p-4 rounded-2xl flex flex-col justify-between text-left h-[135px]"
              >
                <div>
                  <h4 className="text-sm font-semibold text-white truncate">{p.name}</h4>
                  <p className="text-[9px] text-gray-500 font-mono mt-0.5">{p.sku}</p>
                </div>
                <div className="flex justify-between items-end mt-2">
                  <span className="text-xs text-emerald-400 font-bold">${parseFloat(p.price).toFixed(2)}</span>
                  <span className="text-[9px] text-gray-500 bg-[#111827] px-1.5 py-0.5 rounded border border-gray-800">
                    Tax: {parseFloat(p.tax_percent)}%
                  </span>
                </div>
              </button>
            ))}
            {filteredProducts.length === 0 && (
              <div className="col-span-full text-center py-12 text-gray-500 text-sm">
                No matching active products found.
              </div>
            )}
          </div>
        </div>

        {/* RIGHT COLUMN: Cart Summary and Checkout (~30% width) */}
        <div className="w-full lg:w-1/3 flex flex-col glass-panel rounded-2xl overflow-hidden max-h-[85vh] lg:max-h-none">
          {/* Active Cart Title */}
          <div className="p-4 border-b border-gray-800 bg-[#1E293B]/20 flex justify-between items-center">
            <div>
              <h3 className="text-sm font-bold text-white uppercase tracking-wider">Active Cart</h3>
              {store.activeTable && (
                <span className="text-[10px] text-emerald-400 font-bold">Table T-{store.activeTable.table_number}</span>
              )}
            </div>
            {store.cart.length > 0 && (
              <button
                onClick={store.clearCart}
                className="text-xs text-red-400 hover:text-red-300 font-semibold"
              >
                Clear Cart
              </button>
            )}
          </div>

          {/* Cart list */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {store.cart.map((item) => (
              <div key={`${item.product_id}-${item.special_notes}`} className="flex justify-between items-start text-xs border-b border-gray-800/40 pb-2">
                <div className="flex-1 min-w-0 pr-2">
                  <span className="text-white block font-semibold truncate">{item.name}</span>
                  {item.special_notes && (
                    <span className="text-[9px] text-gray-500 block italic truncate">* {item.special_notes}</span>
                  )}
                  <span className="text-[10px] text-gray-500 font-semibold">${item.price.toFixed(2)} each</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-1.5 bg-[#111827] px-1.5 py-1 rounded border border-gray-800">
                    <button
                      onClick={() => store.updateCartQuantity(item.product_id, item.quantity - 1)}
                      className="text-[11px] text-gray-400 hover:text-white px-1 font-bold"
                    >
                      -
                    </button>
                    <span className="text-[11px] text-white font-mono min-w-[12px] text-center">{item.quantity}</span>
                    <button
                      onClick={() => store.updateCartQuantity(item.product_id, item.quantity + 1)}
                      className="text-[11px] text-gray-400 hover:text-white px-1 font-bold"
                    >
                      +
                    </button>
                  </div>
                  <span className="text-emerald-400 font-bold text-right min-w-[50px]">
                    ${(item.price * item.quantity).toFixed(2)}
                  </span>
                </div>
              </div>
            ))}
            {store.cart.length === 0 && (
              <div className="text-center py-16 text-gray-500 text-xs">
                🛒 Shopping cart is empty.<br />Add items from catalog.
              </div>
            )}
          </div>

          {/* Loyalty / Customer Linking */}
          <div className="p-4 bg-[#111827]/40 border-t border-gray-800 space-y-3">
            <div className="flex gap-2">
              <input
                type="text"
                value={phoneQuery}
                onChange={(e) => setPhoneQuery(e.target.value)}
                placeholder="Lookup customer phone..."
                className="flex-1 px-3 py-1.5 bg-[#111827] border border-gray-800 rounded-lg focus:outline-none text-xs text-white"
              />
              <button
                onClick={handleCustomerLookup}
                disabled={lookupLoading}
                className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs font-semibold rounded-lg border border-gray-700"
              >
                Find
              </button>
            </div>

            {loyaltyMessage && (
              <p className="text-[10px] text-amber-400 font-medium text-center">{loyaltyMessage}</p>
            )}

            {loyaltyMessage === "Not found. Enter name to auto-register." && (
              <div className="flex gap-2 bg-[#111827]/80 p-2 rounded-lg border border-gray-800">
                <input
                  type="text"
                  value={regName}
                  onChange={(e) => setRegName(e.target.value)}
                  placeholder="Customer Full Name"
                  className="flex-1 px-3 py-1 bg-[#111827] border border-gray-800 rounded focus:outline-none text-[10px] text-white"
                />
                <button
                  onClick={handleQuickRegister}
                  className="px-2 py-1 bg-emerald-600 hover:bg-emerald-500 text-white text-[10px] font-bold rounded"
                >
                  Register
                </button>
              </div>
            )}

            {store.customer && (
              <div className="flex justify-between items-center gap-2 border border-emerald-950 bg-emerald-950/10 rounded-lg p-2 text-[10px] text-emerald-400">
                <span>Loyalty Points: <b>{store.customer.loyalty_points}</b></span>
                <div className="flex gap-1.5">
                  <input
                    type="number"
                    value={pointsToRedeem || ""}
                    onChange={(e) => setPointsToRedeem(parseInt(e.target.value) || 0)}
                    placeholder="Pts"
                    className="w-12 px-1 py-0.5 bg-[#111827] border border-gray-800 rounded text-center text-white"
                  />
                  <button
                    onClick={handleRedeemPoints}
                    className="px-2 py-0.5 bg-emerald-600 text-white rounded font-bold hover:bg-emerald-500"
                  >
                    Redeem
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Pricing aggregates summary */}
          <div className="p-4 border-t border-gray-800 bg-[#1E293B]/20 space-y-2 text-xs">
            <div className="flex justify-between text-gray-400">
              <span>Subtotal:</span>
              <span>${getSubtotal().toFixed(2)}</span>
            </div>
            <div className="flex justify-between text-gray-400">
              <span>Tax (calculated):</span>
              <span>${getTax().toFixed(2)}</span>
            </div>
            {getDiscount() > 0 && (
              <div className="flex justify-between text-red-400 font-semibold">
                <span>Redeemed Points Discount:</span>
                <span>-${getDiscount().toFixed(2)}</span>
              </div>
            )}
            <div className="flex justify-between text-sm font-bold pt-2 border-t border-gray-800/80 text-white">
              <span>TOTAL BILL:</span>
              <span className="text-emerald-400">${getTotal().toFixed(2)}</span>
            </div>

            {/* Cart Actions */}
            <div className="grid grid-cols-2 gap-2 pt-3">
              <button
                onClick={store.holdCurrentOrder}
                disabled={store.cart.length === 0}
                className="py-2.5 bg-gray-800 hover:bg-gray-700 disabled:bg-gray-900 disabled:cursor-not-allowed border border-gray-700 text-gray-300 disabled:text-gray-600 font-semibold rounded-xl text-xs transition-all"
              >
                Hold Cart
              </button>
              <button
                onClick={handleCheckoutOpen}
                disabled={store.cart.length === 0}
                className="py-2.5 bg-emerald-600 hover:bg-emerald-500 disabled:bg-emerald-800 disabled:cursor-not-allowed text-white font-semibold rounded-xl text-xs transition-all shadow-md shadow-emerald-950/20"
              >
                Pay & Close
              </button>
            </div>
          </div>
        </div>

      </div>

      {/* Product instruction/notes Modal */}
      {selectedProduct && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center p-4 z-50">
          <div className="w-full max-w-sm glass-panel p-6 rounded-2xl shadow-2xl">
            <h3 className="text-lg font-bold text-white mb-1">{selectedProduct.name}</h3>
            <p className="text-gray-400 text-xs mb-4">Price: ${parseFloat(selectedProduct.price).toFixed(2)} each</p>

            <form onSubmit={handleAddItem} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Quantity</label>
                <div className="flex items-center gap-3 bg-[#111827] border border-gray-800 p-2 rounded-xl justify-between">
                  <button
                    type="button"
                    onClick={() => setItemQuantity(Math.max(1, itemQuantity - 1))}
                    className="px-3 py-1 bg-gray-850 hover:bg-gray-850 border border-gray-800 hover:text-white rounded-lg font-bold text-sm"
                  >
                    -
                  </button>
                  <span className="text-white font-bold text-lg">{itemQuantity}</span>
                  <button
                    type="button"
                    onClick={() => setItemQuantity(itemQuantity + 1)}
                    className="px-3 py-1 bg-gray-850 hover:bg-gray-850 border border-gray-800 hover:text-white rounded-lg font-bold text-sm"
                  >
                    +
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Preparation Instructions</label>
                <input
                  type="text"
                  value={itemNotes}
                  onChange={(e) => setItemNotes(e.target.value)}
                  placeholder="e.g. Extra hot, No whip, Oat milk"
                  className="w-full px-4 py-3 bg-[#111827] border border-gray-800 rounded-xl focus:outline-none focus:ring-1 focus:ring-emerald-500/50 focus:border-emerald-500 text-white placeholder-gray-650 text-xs"
                />
              </div>

              <div className="grid grid-cols-2 gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setSelectedProduct(null)}
                  className="py-2.5 bg-gray-850 hover:bg-gray-850 border border-gray-800 text-gray-400 hover:text-white text-xs font-semibold rounded-xl transition-all"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-xl transition-all shadow-md shadow-emerald-950/20"
                >
                  Add to Cart
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Checkout overlay */}
      {showCheckout && store.activeOrder && (
        <CheckoutDrawer
          orderId={store.activeOrder.id}
          totalAmount={getTotal()}
          onPaymentSuccess={() => {
            setShowCheckout(false);
            setShowReceipt(store.activeOrder!.id);
            store.clearCart();
            fetchData();
          }}
          onClose={() => setShowCheckout(false)}
        />
      )}

      {/* Simulated Receipt Preview Modal */}
      {showReceipt && (
        <ReceiptModal
          orderId={showReceipt}
          onClose={() => setShowReceipt(null)}
        />
      )}
    </div>
  );
}
