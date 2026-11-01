import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { api } from "../api";
import { Home } from "../App";
import { DialogProvider } from "../components/ui";
import { demoAdapter } from "./mock";

// The signed-in app on sample data, for design work: npm run dev, then open /demo.html.
api.defaults.adapter = demoAdapter;

createRoot(document.getElementById("root")!).render(
    <StrictMode>
        <DialogProvider>
            {/* demo.html?household=10 opens the sample household instead of "Just me". */}
            <Home initialHouseholdId={Number(new URLSearchParams(window.location.search).get("household")) || null} />
        </DialogProvider>
    </StrictMode>,
);
