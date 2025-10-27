import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import VideoPlayer from "./components/VideoPlayer";
import OverlayEditor from "./components/OverlayEditor";

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<VideoPlayer />} />
        <Route path="/overlays" element={<OverlayEditor />} />
      </Routes>
    </Router>
  );
}

export default App;
