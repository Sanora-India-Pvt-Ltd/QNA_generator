import { useEffect, useState } from "react";
import { getProfile } from "../api/user";

export default function Profile() {
  const [user, setUser] = useState(null);

  useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    try {
      const data = await getProfile();
      setUser(data);
    } catch (err) {
      console.log("Error:", err.response?.data?.message);
    }
  };

  return (
    <div>
      <h1>User Profile</h1>
      {user ? <pre>{JSON.stringify(user, null, 2)}</pre> : "Loading..."}
    </div>
  );
}
