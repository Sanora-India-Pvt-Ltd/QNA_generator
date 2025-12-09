import API from "./sanora";

// LOGIN
export const loginUser = async (email, password) => {
  const res = await API.post("/api/auth/login", { email, password });

  const { accessToken, refreshToken } = res.data.data;

  // Save tokens in browser storage
  localStorage.setItem("accessToken", accessToken);
  localStorage.setItem("refreshToken", refreshToken);

  return res.data.data;
};
