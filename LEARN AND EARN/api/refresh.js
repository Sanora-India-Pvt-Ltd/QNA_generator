import API from "./sanora";

export const refreshAccessToken = async () => {
  try {
    const res = await API.post("/api/auth/refresh-token", {
      refreshToken: localStorage.getItem("refreshToken"),
    });

    const newToken = res.data.data.accessToken;
    localStorage.setItem("accessToken", newToken);

    return newToken;
  } catch (err) {
    console.log("Refresh failed");
    localStorage.clear();
  }
};
