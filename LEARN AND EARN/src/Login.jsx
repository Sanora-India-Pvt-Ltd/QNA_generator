import { useState } from "react";
import { loginUser } from "../api/auth";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  // Email/Password Login
  const handleLogin = async () => {
    try {
      const user = await loginUser(email, password);
      alert("Login Success");
      console.log(user);
    } catch (err) {
      alert(err.response?.data?.message || "Login failed");
    }
  };

  // Google OAuth Login
  const handleGoogleLogin = () => {
    window.location.href = "http://localhost:5000/api/auth/google";
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
      
      {/* Email Login */}
      <input 
        placeholder="Email" 
        onChange={(e) => setEmail(e.target.value)} 
      />

      <input 
        placeholder="Password" 
        type="password" 
        onChange={(e) => setPassword(e.target.value)} 
      />

      <button onClick={handleLogin}>
        Login
      </button>

      <hr />

      {/* Google Login */}
      <button 
        onClick={handleGoogleLogin} 
        style={{ background: "#4285F4", color: "white", padding: "10px", borderRadius: "4px" }}
      >
        Continue with Google
      </button>
    </div>
  );
}
