import { BrowserRouter, Route, Routes } from "react-router-dom";
import Nav from "./components/Nav";
import { PresentationProvider } from "./lib/presentation";
import Cockpit from "./pages/Cockpit";
import MemoryUniverse from "./pages/MemoryUniverse";

export default function App() {
  return (
    <BrowserRouter>
      <PresentationProvider>
        <Nav />
        <Routes>
          <Route path="/" element={<Cockpit />} />
          <Route path="/memory" element={<MemoryUniverse />} />
        </Routes>
      </PresentationProvider>
    </BrowserRouter>
  );
}
