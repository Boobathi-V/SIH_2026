import { BrowserRouter, Routes, Route } from "react-router-dom";

import Home from "./pages/Home";
import PatientDetails from "./pages/PatientDetails";
import UploadImage from "./pages/UploadImage";
import Analysis from "./pages/Analysis";
import Result from "./pages/Result";
import Explain from "./pages/Explain";
import Report from "./pages/Report";

function App() {
  return (
    <BrowserRouter>
      <Routes>

        <Route path="/" element={<Home />} />

        <Route
          path="/patient"
          element={<PatientDetails />}
        />

        <Route
          path="/upload"
          element={<UploadImage />}
        />

        <Route
          path="/analysis"
          element={<Analysis />}
        />

        <Route
          path="/result"
          element={<Result />}
        />

        <Route
          path="/explain"
          element={<Explain />}
        />

        <Route
          path="/report"
          element={<Report />}
        />

      </Routes>
    </BrowserRouter>
  );
}

export default App;