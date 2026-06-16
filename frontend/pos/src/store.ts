import { create } from "zustand";

export interface DecodedToken {
  userId: string;
  username: string;
  role: string;
}

export interface Product {
  id: string;
  sku: string;
  name: string;
  price: string;
  tax_percent: any;
  category_id: string;
  is_available: boolean;
}

export interface Category {
  id: string;
  name: string;
  description?: string;
  display_order?: number;
  is_active?: boolean;
}

export interface Table {
  id: string;
  table_number: number;
  capacity: number;
  location: string;
  status: string; // available, occupied, reserved, cleaning
  current_order_id: string | null;
}

export interface CartItem {
  id?: string;
  product_id: string;
  name: string;
  price: number;
  tax_percent: number;
  quantity: number;
  special_notes: string;
}

export interface Customer {
  id: string;
  phone_number: string;
  email: string;
  name: string;
  loyalty_points: number;
  total_spent: string;
  visit_count: number;
}

export interface Order {
  id: string;
  order_number: string;
  order_type: string;
  table_id: string | null;
  customer_id: string | null;
  status: string;
  subtotal: string;
  tax_amount: string;
  discount_amount: string;
  total_amount: string;
  notes: string;
  is_hold: boolean;
  completed_at: string | null;
}

export interface HeldOrder {
  id: string;
  order_number: string;
  table_id: string | null;
  table_number?: number;
  order_type: string;
  cart: CartItem[];
  customer: Customer | null;
  discount: { amount: number; percentage: number; code: string; points_redeemed?: number } | null;
  notes: string;
}

export interface POSState {
  token: string | null;
  user: DecodedToken | null;
  orderType: "dine_in" | "take_away" | "delivery";
  activeTable: Table | null;
  cart: CartItem[];
  customer: Customer | null;
  discount: { amount: number; percentage: number; code: string; points_redeemed?: number } | null;
  activeOrder: Order | null;
  categories: Category[];
  products: Product[];
  tables: Table[];
  heldOrders: HeldOrder[];

  // Actions
  setToken: (token: string | null) => void;
  setOrderType: (type: "dine_in" | "take_away" | "delivery") => void;
  setActiveTable: (table: Table | null) => void;
  setCustomer: (customer: Customer | null) => void;
  setDiscount: (discount: { amount: number; percentage: number; code: string; points_redeemed?: number } | null) => void;
  setActiveOrder: (order: Order | null) => void;
  setCatalog: (categories: Category[], products: Product[]) => void;
  setTables: (tables: Table[]) => void;

  // Cart actions
  addToCart: (product: Product, quantity: number, specialNotes: string) => void;
  removeFromCart: (productId: string) => void;
  updateCartQuantity: (productId: string, quantity: number) => void;
  clearCart: () => void;
  loadCartFromOrder: (order: Order, items: any[]) => void;

  // Hold queue
  holdCurrentOrder: () => void;
  resumeHeldOrder: (heldOrderId: string) => void;
}

function decodeToken(token: string): DecodedToken | null {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    const payload = JSON.parse(atob(parts[1].replace(/-/g, "+").replace(/_/g, "/")));
    return {
      userId: payload.user_id,
      username: payload.username,
      role: payload.role,
    };
  } catch (e) {
    return null;
  }
}

const savedToken = localStorage.getItem("pandacafe_pos_token");

export const usePOSStore = create<POSState>((set, get) => ({
  token: savedToken,
  user: savedToken ? decodeToken(savedToken) : null,
  orderType: "dine_in",
  activeTable: null,
  cart: [],
  customer: null,
  discount: null,
  activeOrder: null,
  categories: [],
  products: [],
  tables: [],
  heldOrders: [],

  setToken: (token) => {
    if (token) {
      localStorage.setItem("pandacafe_pos_token", token);
      set({ token, user: decodeToken(token) });
    } else {
      localStorage.removeItem("pandacafe_pos_token");
      set({ token: null, user: null });
    }
  },

  setOrderType: (type) => set({ orderType: type, activeTable: type !== "dine_in" ? null : get().activeTable }),
  setActiveTable: (table) => set({ activeTable: table, orderType: table ? "dine_in" : get().orderType }),
  setCustomer: (customer) => set({ customer }),
  setDiscount: (discount) => set({ discount }),
  setActiveOrder: (order) => set({ activeOrder: order }),
  setCatalog: (categories, products) => set({ 
    categories: Array.isArray(categories) ? categories : [], 
    products: Array.isArray(products) ? products : [] 
  }),
  setTables: (tables) => set({ tables: Array.isArray(tables) ? tables : [] }),

  addToCart: (product, quantity, specialNotes) => {
    const cart = get().cart;
    const existingIndex = cart.findIndex(
      (item) => item.product_id === product.id && item.special_notes === specialNotes
    );

    if (existingIndex > -1) {
      const updatedCart = [...cart];
      updatedCart[existingIndex].quantity += quantity;
      set({ cart: updatedCart });
    } else {
      set({
        cart: [
          ...cart,
          {
            product_id: product.id,
            name: product.name,
            price: parseFloat(product.price),
            tax_percent: parseFloat(product.tax_percent) || 0,
            quantity,
            special_notes: specialNotes,
          },
        ],
      });
    }
  },

  removeFromCart: (productId) => {
    set({ cart: get().cart.filter((item) => item.product_id !== productId) });
  },

  updateCartQuantity: (productId, quantity) => {
    if (quantity <= 0) {
      get().removeFromCart(productId);
      return;
    }
    set({
      cart: get().cart.map((item) => (item.product_id === productId ? { ...item, quantity } : item)),
    });
  },

  clearCart: () => set({ cart: [], customer: null, discount: null, activeOrder: null }),

  loadCartFromOrder: (order, items) => {
    const mappedCart: CartItem[] = items.map((item: any) => ({
      id: item.id,
      product_id: item.product_id,
      name: item.product ? item.product.name : "Item",
      price: parseFloat(item.unit_price),
      tax_percent: parseFloat(item.tax_percent) || 0,
      quantity: item.quantity,
      special_notes: item.special_notes || "",
    }));

    set({
      activeOrder: order,
      orderType: order.order_type as any,
      cart: mappedCart,
      discount: order.discount_amount && parseFloat(order.discount_amount) > 0
        ? { amount: parseFloat(order.discount_amount), percentage: 0, code: "Redemption" }
        : null,
    });
  },

  holdCurrentOrder: () => {
    const { cart, activeTable, orderType, customer, discount, heldOrders } = get();
    if (cart.length === 0) return;

    const newHeld: HeldOrder = {
      id: uuidv4(),
      order_number: `HOLD-${Date.now().toString().slice(-5)}`,
      table_id: activeTable ? activeTable.id : null,
      table_number: activeTable ? activeTable.table_number : undefined,
      order_type: orderType,
      cart,
      customer,
      discount,
      notes: "Held Order",
    };

    set({
      heldOrders: [...heldOrders, newHeld],
      cart: [],
      activeTable: null,
      customer: null,
      discount: null,
      activeOrder: null,
    });
  },

  resumeHeldOrder: (heldOrderId) => {
    const { heldOrders } = get();
    const target = heldOrders.find((o) => o.id === heldOrderId);
    if (!target) return;

    let targetTable: Table | null = null;
    if (target.table_id) {
      targetTable = get().tables.find((t) => t.id === target.table_id) || null;
    }

    set({
      cart: target.cart,
      activeTable: targetTable,
      orderType: target.order_type as any,
      customer: target.customer,
      discount: target.discount,
      heldOrders: heldOrders.filter((o) => o.id !== heldOrderId),
      activeOrder: null,
    });
  },
}));

// Helper to generate local temporary UUIDs
function uuidv4() {
  return "10000000-1000-4000-8000-100000000000".replace(/[018]/g, (c: any) =>
    (c ^ (crypto.getRandomValues(new Uint8Array(1))[0] & (15 >> (c / 4)))).toString(16)
  );
}
