import axios from "axios";
import { usePOSStore } from "./store";

export const API_URL = window.location.port === "3000" ? "/api/v1" : `${window.location.protocol}//${window.location.host}/api/v1`;

const api = axios.create({
  baseURL: API_URL,
});

api.interceptors.request.use((config) => {
  const token = usePOSStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default api;
