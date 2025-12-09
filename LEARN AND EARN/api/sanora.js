import axios from "axios";

const API = axios.create({
  baseURL: "https://api.sanoraindia.com",
});

// Attach access token automatically
API.interceptors.request.use((config) => {
  const token = localStorage.getItem("accessToken");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export default API;
