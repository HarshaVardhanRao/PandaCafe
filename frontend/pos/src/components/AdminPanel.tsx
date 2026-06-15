import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";
import { usePOSStore, Product, Category } from "../store";

export default function AdminPanel() {
  const navigate = useNavigate();
  const store = usePOSStore();

  const [activeTab, setActiveTab] = useState<"products" | "categories">("products");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Data states
  const [products, setProducts] = useState<any[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);

  // Search & Filter
  const [prodSearch, setProdSearch] = useState("");
  const [prodCatFilter, setProdCatFilter] = useState("all");
  const [catSearch, setCatSearch] = useState("");

  // Category Form Modal States
  const [showCatModal, setShowCatModal] = useState(false);
  const [editingCategory, setEditingCategory] = useState<Category | null>(null);
  const [catName, setCatName] = useState("");
  const [catDesc, setCatDesc] = useState("");
  const [catDisplayOrder, setCatDisplayOrder] = useState(0);
  const [catIsActive, setCatIsActive] = useState(true);

  // Product Form Modal States
  const [showProdModal, setShowProdModal] = useState(false);
  const [editingProduct, setEditingProduct] = useState<any | null>(null);
  const [prodSku, setProdSku] = useState("");
  const [prodName, setProdName] = useState("");
  const [prodDesc, setProdDesc] = useState("");
  const [prodCatId, setProdCatId] = useState("");
  const [prodPrice, setProdPrice] = useState("");
  const [prodTaxPercent, setProdTaxPercent] = useState("0");
  const [prodPrepTime, setProdPrepTime] = useState("5");
  const [prodIsAvailable, setProdIsAvailable] = useState(true);
  const [prodIsActive, setProdIsActive] = useState(true);

  // Delete Confirmation States
  const [confirmDelete, setConfirmDelete] = useState<{ type: "product" | "category"; id: string; name: string } | null>(null);

  // Fetch all categories and products (including inactive/unavailable ones for administration)
  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [catsRes, prodsRes] = await Promise.all([
        api.get("/products/categories?active_only=false"),
        api.get("/products?active_only=false"),
      ]);
      setCategories(catsRes.data);
      setProducts(prodsRes.data);

      // Sync categories to global store in case they've changed
      // (only active ones for Cashier catalog)
      const activeCats = catsRes.data.filter((c: any) => c.is_active);
      const activeProds = prodsRes.data.filter((p: any) => p.is_active && p.is_available);
      store.setCatalog(activeCats, activeProds);
    } catch (e: any) {
      setError(e.response?.data?.detail || "Failed to load database items.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const triggerToast = (msg: string, type: "success" | "error") => {
    if (type === "success") {
      setSuccess(msg);
      setTimeout(() => setSuccess(null), 4000);
    } else {
      setError(msg);
      setTimeout(() => setError(null), 4000);
    }
  };

  // --- Category CRUD Handlers ---

  const handleOpenAddCategory = () => {
    setEditingCategory(null);
    setCatName("");
    setCatDesc("");
    setCatDisplayOrder(0);
    setCatIsActive(true);
    setShowCatModal(true);
  };

  const handleOpenEditCategory = (cat: Category | any) => {
    setEditingCategory(cat);
    setCatName(cat.name);
    setCatDesc(cat.description || "");
    setCatDisplayOrder(cat.display_order || 0);
    setCatIsActive(cat.is_active);
    setShowCatModal(true);
  };

  const handleSaveCategory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!catName.trim()) {
      triggerToast("Category name is required.", "error");
      return;
    }

    const payload = {
      name: catName.trim(),
      description: catDesc.trim() || null,
      display_order: Number(catDisplayOrder),
      is_active: catIsActive,
    };

    setLoading(true);
    try {
      if (editingCategory) {
        await api.put(`/products/categories/${editingCategory.id}`, payload);
        triggerToast("Category updated successfully!", "success");
      } else {
        await api.post("/products/categories", payload);
        triggerToast("Category created successfully!", "success");
      }
      setShowCatModal(false);
      loadData();
    } catch (err: any) {
      triggerToast(err.response?.data?.detail || "Failed to save category.", "error");
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteCategory = async (id: string) => {
    setLoading(true);
    try {
      await api.delete(`/products/categories/${id}`);
      triggerToast("Category deleted successfully!", "success");
      setConfirmDelete(null);
      loadData();
    } catch (err: any) {
      triggerToast(err.response?.data?.detail || "Failed to delete category.", "error");
    } finally {
      setLoading(false);
    }
  };

  // --- Product CRUD Handlers ---

  const handleOpenAddProduct = () => {
    setEditingProduct(null);
    setProdSku(`PROD-${Date.now().toString().slice(-6)}`);
    setProdName("");
    setProdDesc("");
    setProdCatId(categories[0]?.id || "");
    setProdPrice("");
    setProdTaxPercent("0");
    setProdPrepTime("5");
    setProdIsAvailable(true);
    setProdIsActive(true);
    setShowProdModal(true);
  };

  const handleOpenEditProduct = (prod: any) => {
    setEditingProduct(prod);
    setProdSku(prod.sku);
    setProdName(prod.name);
    setProdDesc(prod.description || "");
    setProdCatId(prod.category_id);
    setProdPrice(prod.price.toString());
    setProdTaxPercent((prod.tax_percent ?? 0).toString());
    setProdPrepTime((prod.preparation_time_minutes ?? 5).toString());
    setProdIsAvailable(prod.is_available);
    setProdIsActive(prod.is_active);
    setShowProdModal(true);
  };

  const handleSaveProduct = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prodSku.trim() || !prodName.trim() || !prodCatId || !prodPrice) {
      triggerToast("Please fill in all required fields.", "error");
      return;
    }

    const priceNum = parseFloat(prodPrice);
    if (isNaN(priceNum) || priceNum <= 0) {
      triggerToast("Price must be a valid number greater than 0.", "error");
      return;
    }

    const taxNum = parseFloat(prodTaxPercent);
    if (isNaN(taxNum) || taxNum < 0 || taxNum > 100) {
      triggerToast("Tax percent must be between 0 and 100.", "error");
      return;
    }

    const prepTimeNum = parseInt(prodPrepTime);
    if (isNaN(prepTimeNum) || prepTimeNum < 0) {
      triggerToast("Preparation time must be a positive integer.", "error");
      return;
    }

    const payload: any = {
      name: prodName.trim(),
      description: prodDesc.trim() || null,
      category_id: prodCatId,
      price: priceNum,
      tax_percent: taxNum,
      preparation_time_minutes: prepTimeNum,
    };

    // Include creation fields only or support edit toggle endpoints
    if (!editingProduct) {
      payload.sku = prodSku.trim();
    } else {
      payload.is_available = prodIsAvailable;
      payload.is_active = prodIsActive;
    }

    setLoading(true);
    try {
      if (editingProduct) {
        await api.put(`/products/${editingProduct.id}`, payload);
        triggerToast("Product updated successfully!", "success");
      } else {
        await api.post("/products", payload);
        triggerToast("Product created successfully!", "success");
      }
      setShowProdModal(false);
      loadData();
    } catch (err: any) {
      triggerToast(err.response?.data?.detail || "Failed to save product.", "error");
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteProduct = async (id: string) => {
    setLoading(true);
    try {
      await api.delete(`/products/${id}`);
      triggerToast("Product deleted successfully!", "success");
      setConfirmDelete(null);
      loadData();
    } catch (err: any) {
      triggerToast(err.response?.data?.detail || "Failed to delete product.", "error");
    } finally {
      setLoading(false);
    }
  };

  // Filter Products
  const filteredProducts = products.filter((p) => {
    const matchSearch =
      p.name.toLowerCase().includes(prodSearch.toLowerCase()) ||
      p.sku.toLowerCase().includes(prodSearch.toLowerCase()) ||
      (p.description && p.description.toLowerCase().includes(prodSearch.toLowerCase()));
    const matchCat = prodCatFilter === "all" || p.category_id === prodCatFilter;
    return matchSearch && matchCat;
  });

  // Filter Categories
  const filteredCategories = categories.filter((c) =>
    c.name.toLowerCase().includes(catSearch.toLowerCase()) ||
    (c.description && c.description.toLowerCase().includes(catSearch.toLowerCase()))
  );

  return (
    <div className="min-h-screen flex flex-col bg-[#070A13] text-gray-200">
      {/* Header */}
      <header className="px-6 py-4 bg-[#111827]/80 border-b border-gray-800 flex justify-between items-center z-25 sticky top-0 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <span className="text-2xl">🐼</span>
          <div>
            <h1 className="text-xl font-bold text-white tracking-wide">PandaCafe</h1>
            <p className="text-[10px] text-emerald-400 font-mono tracking-wider font-semibold uppercase">Admin Portal</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate("/")}
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white border border-emerald-500/30 rounded-xl transition-all text-xs font-semibold flex items-center gap-2"
          >
            <span>🏠</span> Return to Cashier
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 p-6 max-w-7xl w-full mx-auto space-y-6">
        {/* Alerts / Toast Messages */}
        {error && (
          <div className="bg-red-950/40 border border-red-500/50 text-red-300 p-4 rounded-xl text-sm flex items-center justify-between animate-fadeIn">
            <span>⚠️ {error}</span>
            <button onClick={() => setError(null)} className="text-red-400 hover:text-white font-bold">&times;</button>
          </div>
        )}
        {success && (
          <div className="bg-emerald-950/40 border border-emerald-500/50 text-emerald-300 p-4 rounded-xl text-sm flex items-center justify-between animate-fadeIn">
            <span>✅ {success}</span>
            <button onClick={() => setSuccess(null)} className="text-emerald-400 hover:text-white font-bold">&times;</button>
          </div>
        )}

        {/* Dashboard Tabs & Controls */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-[#111827]/60 p-4 rounded-2xl border border-gray-800 backdrop-blur-sm">
          <div className="flex bg-[#070A13] p-1 rounded-xl border border-gray-850">
            <button
              onClick={() => setActiveTab("products")}
              className={`px-5 py-2.5 rounded-lg text-sm font-semibold transition-all ${
                activeTab === "products"
                  ? "bg-emerald-600 text-white shadow-lg shadow-emerald-950/20"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              🍔 Manage Menu Products
            </button>
            <button
              onClick={() => setActiveTab("categories")}
              className={`px-5 py-2.5 rounded-lg text-sm font-semibold transition-all ${
                activeTab === "categories"
                  ? "bg-emerald-600 text-white shadow-lg shadow-emerald-950/20"
                  : "text-gray-400 hover:text-white"
              }`}
            >
              📁 Manage Categories
            </button>
          </div>

          <div className="flex gap-2 w-full md:w-auto">
            {activeTab === "products" ? (
              <button
                onClick={handleOpenAddProduct}
                disabled={categories.length === 0}
                className="w-full md:w-auto px-4 py-2.5 bg-emerald-600 hover:bg-emerald-500 disabled:bg-gray-800 disabled:text-gray-500 disabled:cursor-not-allowed text-white text-sm font-semibold rounded-xl transition-all flex items-center justify-center gap-1.5 shadow-md shadow-emerald-950/25"
              >
                <span>➕</span> Add Product
              </button>
            ) : (
              <button
                onClick={handleOpenAddCategory}
                className="w-full md:w-auto px-4 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-semibold rounded-xl transition-all flex items-center justify-center gap-1.5 shadow-md shadow-emerald-950/25"
              >
                <span>➕</span> Add Category
              </button>
            )}
          </div>
        </div>

        {/* --- PRODUCTS VIEW --- */}
        {activeTab === "products" && (
          <div className="glass-panel p-6 rounded-2xl border border-gray-800 space-y-4">
            {/* Search and Filters */}
            <div className="flex flex-col md:flex-row gap-4">
              <input
                type="text"
                placeholder="Search products by SKU, Name or Desc..."
                value={prodSearch}
                onChange={(e) => setProdSearch(e.target.value)}
                className="flex-1 px-4 py-2.5 bg-[#111827]/80 border border-gray-800 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 text-white text-sm transition-all"
              />
              <select
                value={prodCatFilter}
                onChange={(e) => setProdCatFilter(e.target.value)}
                className="px-4 py-2.5 bg-[#111827]/80 border border-gray-800 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500/50 text-white text-sm cursor-pointer"
              >
                <option value="all">All Categories</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>

            {/* Products Table */}
            <div className="overflow-x-auto rounded-xl border border-gray-850 bg-[#111827]/30">
              {loading && products.length === 0 ? (
                <div className="text-center py-12">
                  <svg className="animate-spin h-8 w-8 text-emerald-500 mx-auto mb-3" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  <p className="text-gray-400 text-sm">Fetching catalog...</p>
                </div>
              ) : filteredProducts.length === 0 ? (
                <div className="text-center py-12 text-gray-500 text-sm">
                  No products found. Add products to display them here.
                </div>
              ) : (
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="bg-[#111827] text-gray-400 uppercase tracking-wider border-b border-gray-850">
                      <th className="p-4 font-bold">SKU</th>
                      <th className="p-4 font-bold">Name</th>
                      <th className="p-4 font-bold">Category</th>
                      <th className="p-4 font-bold">Price</th>
                      <th className="p-4 font-bold">Tax Rate</th>
                      <th className="p-4 font-bold">Status</th>
                      <th className="p-4 font-bold text-center">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-850">
                    {filteredProducts.map((p) => {
                      const cat = categories.find((c) => c.id === p.category_id);
                      return (
                        <tr key={p.id} className="hover:bg-gray-850/30 transition-all">
                          <td className="p-4 font-mono font-medium text-gray-400">{p.sku}</td>
                          <td className="p-4">
                            <div className="font-semibold text-white">{p.name}</div>
                            {p.description && <div className="text-[10px] text-gray-500 mt-0.5 line-clamp-1">{p.description}</div>}
                          </td>
                          <td className="p-4 text-gray-300 font-medium">{cat ? cat.name : "Unassigned"}</td>
                          <td className="p-4 text-emerald-400 font-bold">${parseFloat(p.price).toFixed(2)}</td>
                          <td className="p-4 text-gray-400">{parseFloat(p.tax_percent ?? 0)}%</td>
                          <td className="p-4">
                            <div className="flex gap-2">
                              <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold ${
                                p.is_available ? "bg-emerald-950/50 text-emerald-400 border border-emerald-900/50" : "bg-red-950/50 text-red-400 border border-red-900/50"
                              }`}>
                                {p.is_available ? "Available" : "Sold Out"}
                              </span>
                              <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold ${
                                p.is_active ? "bg-blue-950/50 text-blue-400 border border-blue-900/50" : "bg-gray-850 text-gray-400 border border-gray-800"
                              }`}>
                                {p.is_active ? "Active" : "Archived"}
                              </span>
                            </div>
                          </td>
                          <td className="p-4">
                            <div className="flex gap-2 justify-center">
                              <button
                                onClick={() => handleOpenEditProduct(p)}
                                className="px-2.5 py-1 bg-gray-850 border border-gray-800 hover:bg-emerald-600 hover:text-white rounded-md transition-all text-[10px] font-bold"
                              >
                                Edit
                              </button>
                              <button
                                onClick={() => setConfirmDelete({ type: "product", id: p.id, name: p.name })}
                                className="px-2.5 py-1 bg-gray-850 border border-gray-850 hover:bg-red-950 hover:border-red-900 hover:text-red-400 rounded-md transition-all text-[10px] font-bold"
                              >
                                Delete
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        )}

        {/* --- CATEGORIES VIEW --- */}
        {activeTab === "categories" && (
          <div className="glass-panel p-6 rounded-2xl border border-gray-800 space-y-4">
            {/* Search */}
            <div className="flex gap-4">
              <input
                type="text"
                placeholder="Search categories by name or description..."
                value={catSearch}
                onChange={(e) => setCatSearch(e.target.value)}
                className="flex-1 px-4 py-2.5 bg-[#111827]/80 border border-gray-800 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 text-white text-sm transition-all"
              />
            </div>

            {/* Categories Table */}
            <div className="overflow-x-auto rounded-xl border border-gray-850 bg-[#111827]/30">
              {loading && categories.length === 0 ? (
                <div className="text-center py-12">
                  <svg className="animate-spin h-8 w-8 text-emerald-500 mx-auto mb-3" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  <p className="text-gray-400 text-sm">Fetching categories...</p>
                </div>
              ) : filteredCategories.length === 0 ? (
                <div className="text-center py-12 text-gray-500 text-sm">
                  No categories found. Add categories to display them here.
                </div>
              ) : (
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="bg-[#111827] text-gray-400 uppercase tracking-wider border-b border-gray-850">
                      <th className="p-4 font-bold">Category Name</th>
                      <th className="p-4 font-bold">Description</th>
                      <th className="p-4 font-bold">Display Order</th>
                      <th className="p-4 font-bold">Status</th>
                      <th className="p-4 font-bold text-center">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-850">
                    {filteredCategories.map((c) => (
                      <tr key={c.id} className="hover:bg-gray-850/30 transition-all">
                        <td className="p-4 font-semibold text-white text-sm">{c.name}</td>
                        <td className="p-4 text-gray-400 max-w-sm truncate">{c.description || <span className="text-gray-600 font-light italic">No description</span>}</td>
                        <td className="p-4 text-gray-300 font-mono font-semibold">{(c as any).display_order}</td>
                        <td className="p-4">
                          <span className={`px-2.5 py-0.5 rounded-full text-[9px] font-bold ${(c as any).is_active ? "bg-emerald-950/50 text-emerald-400 border border-emerald-900/50" : "bg-gray-850 text-gray-400 border border-gray-850"}`}>
                            {(c as any).is_active ? "Active" : "Archived"}
                          </span>
                        </td>
                        <td className="p-4">
                          <div className="flex gap-2 justify-center">
                            <button
                              onClick={() => handleOpenEditCategory(c)}
                              className="px-2.5 py-1 bg-gray-850 border border-gray-800 hover:bg-emerald-600 hover:text-white rounded-md transition-all text-[10px] font-bold"
                            >
                              Edit
                            </button>
                            <button
                              onClick={() => setConfirmDelete({ type: "category", id: c.id, name: c.name })}
                              className="px-2.5 py-1 bg-gray-850 border border-gray-855 hover:bg-red-950 hover:border-red-900 hover:text-red-400 rounded-md transition-all text-[10px] font-bold"
                            >
                              Delete
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        )}
      </main>

      {/* --- CATEGORY FORM MODAL --- */}
      {showCatModal && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center p-4 z-50">
          <div className="w-full max-w-md glass-panel p-6 rounded-2xl border border-gray-800 shadow-2xl animate-fadeIn">
            <h3 className="text-lg font-bold text-white mb-4">
              {editingCategory ? "✏️ Edit Product Category" : "📁 Create New Category"}
            </h3>

            <form onSubmit={handleSaveCategory} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Category Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Beverages, Pastries"
                  value={catName}
                  onChange={(e) => setCatName(e.target.value)}
                  className="w-full px-4 py-2.5 bg-[#111827] border border-gray-800 rounded-xl focus:outline-none focus:ring-1 focus:ring-emerald-500 text-white text-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Description</label>
                <textarea
                  placeholder="Describe category items..."
                  value={catDesc}
                  onChange={(e) => setCatDesc(e.target.value)}
                  rows={3}
                  className="w-full px-4 py-2.5 bg-[#111827] border border-gray-800 rounded-xl focus:outline-none focus:ring-1 focus:ring-emerald-500 text-white text-sm resize-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Display Order</label>
                  <input
                    type="number"
                    min="0"
                    value={catDisplayOrder}
                    onChange={(e) => setCatDisplayOrder(parseInt(e.target.value) || 0)}
                    className="w-full px-4 py-2.5 bg-[#111827] border border-gray-800 rounded-xl focus:outline-none focus:ring-1 focus:ring-emerald-500 text-white text-sm"
                  />
                </div>
                <div className="flex flex-col justify-end">
                  <label className="flex items-center gap-2 text-sm text-gray-300 font-semibold cursor-pointer select-none pb-3">
                    <input
                      type="checkbox"
                      checked={catIsActive}
                      onChange={(e) => setCatIsActive(e.target.checked)}
                      className="w-4 h-4 rounded border-gray-800 text-emerald-600 bg-[#111827] focus:ring-0 focus:ring-offset-0"
                    />
                    Is Active Category
                  </label>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2 pt-4">
                <button
                  type="button"
                  onClick={() => setShowCatModal(false)}
                  className="py-2.5 bg-gray-850 border border-gray-800 text-gray-400 hover:text-white text-xs font-semibold rounded-xl transition-all"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="py-2.5 bg-emerald-600 hover:bg-emerald-500 disabled:bg-emerald-800 text-white text-xs font-semibold rounded-xl transition-all flex justify-center items-center gap-1.5"
                >
                  {loading ? "Saving..." : "Save Category"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* --- PRODUCT FORM MODAL --- */}
      {showProdModal && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center p-4 z-50 overflow-y-auto">
          <div className="w-full max-w-lg bg-[#070A13] border border-gray-800 p-6 rounded-2xl shadow-2xl my-8 animate-fadeIn max-h-[90vh] overflow-y-auto">
            <h3 className="text-lg font-bold text-white mb-4">
              {editingProduct ? "✏️ Edit Product Details" : "🍔 Create New Product"}
            </h3>

            <form onSubmit={handleSaveProduct} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">SKU Code *</label>
                  <input
                    type="text"
                    required
                    disabled={!!editingProduct}
                    placeholder="e.g. COFFEE-001"
                    value={prodSku}
                    onChange={(e) => setProdSku(e.target.value)}
                    className="w-full px-4 py-2.5 bg-[#111827] border border-gray-800 disabled:bg-gray-900 disabled:text-gray-500 rounded-xl focus:outline-none focus:ring-1 focus:ring-emerald-500 text-white text-sm font-mono"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Product Name *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Flat White"
                    value={prodName}
                    onChange={(e) => setProdName(e.target.value)}
                    className="w-full px-4 py-2.5 bg-[#111827] border border-gray-800 rounded-xl focus:outline-none focus:ring-1 focus:ring-emerald-500 text-white text-sm"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Description</label>
                <input
                  type="text"
                  placeholder="e.g. Double shot espresso with steamed milk"
                  value={prodDesc}
                  onChange={(e) => setProdDesc(e.target.value)}
                  className="w-full px-4 py-2.5 bg-[#111827] border border-gray-800 rounded-xl focus:outline-none focus:ring-1 focus:ring-emerald-500 text-white text-sm"
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Category *</label>
                  <select
                    value={prodCatId}
                    onChange={(e) => setProdCatId(e.target.value)}
                    className="w-full px-4 py-2.5 bg-[#111827] border border-gray-800 rounded-xl focus:outline-none focus:ring-1 focus:ring-emerald-500 text-white text-sm"
                  >
                    {categories.map((c) => (
                      <option key={c.id} value={c.id}>{c.name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Price ($) *</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0.01"
                    required
                    placeholder="0.00"
                    value={prodPrice}
                    onChange={(e) => setProdPrice(e.target.value)}
                    className="w-full px-4 py-2.5 bg-[#111827] border border-gray-800 rounded-xl focus:outline-none focus:ring-1 focus:ring-emerald-500 text-white text-sm font-semibold text-emerald-400"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Tax Percent (%)</label>
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    max="100"
                    value={prodTaxPercent}
                    onChange={(e) => setProdTaxPercent(e.target.value)}
                    className="w-full px-4 py-2.5 bg-[#111827] border border-gray-800 rounded-xl focus:outline-none focus:ring-1 focus:ring-emerald-500 text-white text-sm"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
                <div>
                  <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Prep Time (Min)</label>
                  <input
                    type="number"
                    min="0"
                    value={prodPrepTime}
                    onChange={(e) => setProdPrepTime(e.target.value)}
                    className="w-full px-4 py-2.5 bg-[#111827] border border-gray-800 rounded-xl focus:outline-none focus:ring-1 focus:ring-emerald-500 text-white text-sm"
                  />
                </div>
                <div className="flex flex-col justify-end">
                  <label className="flex items-center gap-2 text-sm text-gray-300 font-semibold cursor-pointer select-none pb-3">
                    <input
                      type="checkbox"
                      checked={prodIsAvailable}
                      onChange={(e) => setProdIsAvailable(e.target.checked)}
                      className="w-4 h-4 rounded border-gray-800 text-emerald-600 bg-[#111827] focus:ring-0 focus:ring-offset-0"
                    />
                    Is Available (In Stock)
                  </label>
                </div>
                <div className="flex flex-col justify-end">
                  <label className="flex items-center gap-2 text-sm text-gray-300 font-semibold cursor-pointer select-none pb-3">
                    <input
                      type="checkbox"
                      checked={prodIsActive}
                      onChange={(e) => setProdIsActive(e.target.checked)}
                      className="w-4 h-4 rounded border-gray-800 text-emerald-600 bg-[#111827] focus:ring-0 focus:ring-offset-0"
                    />
                    Is Active (Visible)
                  </label>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2 pt-4">
                <button
                  type="button"
                  onClick={() => setShowProdModal(false)}
                  className="py-2.5 bg-gray-850 border border-gray-800 text-gray-400 hover:text-white text-xs font-semibold rounded-xl transition-all"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="py-2.5 bg-emerald-600 hover:bg-emerald-500 disabled:bg-emerald-800 text-white text-xs font-semibold rounded-xl transition-all flex justify-center items-center gap-1.5"
                >
                  {loading ? "Saving..." : "Save Product"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* --- CONFIRM DELETE MODAL --- */}
      {confirmDelete && (
        <div className="fixed inset-0 bg-black/85 flex items-center justify-center p-4 z-55">
          <div className="w-full max-w-sm bg-[#111827] border border-red-950 p-6 rounded-2xl shadow-2xl animate-scaleIn">
            <div className="w-12 h-12 rounded-full bg-red-950/40 border border-red-900 flex items-center justify-center text-red-500 text-xl mx-auto mb-4">
              🗑️
            </div>
            <h3 className="text-base font-bold text-white text-center mb-2">Delete Confirmation</h3>
            <p className="text-gray-400 text-xs text-center mb-6 leading-relaxed">
              Are you sure you want to permanently delete the {confirmDelete.type} <span className="font-bold text-white">"{confirmDelete.name}"</span>? This action cannot be undone.
            </p>

            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setConfirmDelete(null)}
                className="py-2.5 bg-gray-850 border border-gray-800 text-gray-400 hover:text-white text-xs font-semibold rounded-xl transition-all"
              >
                No, Keep It
              </button>
              <button
                type="button"
                onClick={() =>
                  confirmDelete.type === "product"
                    ? handleDeleteProduct(confirmDelete.id)
                    : handleDeleteCategory(confirmDelete.id)
                }
                disabled={loading}
                className="py-2.5 bg-red-750 hover:bg-red-700 disabled:bg-red-900 text-white text-xs font-bold rounded-xl transition-all flex justify-center items-center"
              >
                {loading ? "Deleting..." : "Yes, Delete"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
