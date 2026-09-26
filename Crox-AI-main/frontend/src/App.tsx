import { Route, Routes } from "react-router-dom";
import Landing from "./pages/Landing";
import Chat from "./pages/Chat";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/app" element={<Chat />} />
    </Routes>
  );
}
