function $(id) {
  return document.getElementById(id);
}

function fmtTime(unixSeconds) {
  if (!unixSeconds) return "—";
  const d = new Date(unixSeconds * 1000);
  return d.toLocaleString();
}

async function checkHealth() {
  const pill = $("healthPill");
  try {
    const res = await fetch("/api/health");
    const data = await res.json();
    if (!data.ok) throw new Error("health not ok");
    pill.textContent = "API OK";
    pill.classList.add("ok");
  } catch (e) {
    pill.textContent = "API error";
    pill.classList.add("bad");
  }
}

function setDecision(el, decision) {
  el.textContent = decision || "—";
  el.classList.remove("good", "bad");
  if (decision === "IRRIGATE_ON") el.classList.add("good");
  if (decision === "IRRIGATE_OFF") el.classList.add("bad");
}

async function refreshLatestEsp32() {
  try {
    const res = await fetch("/api/esp32/latest", { cache: "no-store" });
    const data = await res.json();
    const latest = data.latest;
    if (!latest) return;

    $("esp32Device").textContent = latest.source ?? "esp32";
    $("esp32Received").textContent = fmtTime(latest.received_at_unix);
    $("esp32Temp").textContent = Number(latest.temperature).toFixed(1);
    $("esp32Hum").textContent = Number(latest.humidity).toFixed(1);
    $("esp32Prob").textContent = Number(latest.probability).toFixed(4);
    setDecision($("esp32Decision"), latest.decision);
  } catch (e) {
    // ignore transient errors
  }
}

function wireTabs() {
  const tabs = document.querySelectorAll(".tab");
  tabs.forEach((btn) => {
    btn.addEventListener("click", () => {
      tabs.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const name = btn.dataset.tab;
      document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
      const panel = document.getElementById(`tab-${name}`);
      if (panel) panel.classList.add("active");
    });
  });
}

function wireManualForm() {
  const form = $("manualForm");
  const out = $("manualResult");
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    out.innerHTML = `<div class="muted">Predicting…</div>`;

    const fd = new FormData(form);
    const temperature = Number(fd.get("temperature"));
    const humidity = Number(fd.get("humidity"));
    const soil = Number(fd.get("soil"));

    try {
      const res = await fetch("/api/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ temperature, humidity, soil }),
      });
      const data = await res.json();
      if (!data.ok) throw new Error(data.error || "predict failed");
      const r = data.result;
      out.innerHTML = `
        <div class="grid" style="grid-template-columns: repeat(2, minmax(0, 1fr));">
          <div class="kv"><div class="k">z</div><div class="v">${Number(r.z).toFixed(4)}</div></div>
          <div class="kv"><div class="k">Probability</div><div class="v">${Number(r.probability).toFixed(4)}</div></div>
          <div class="kv"><div class="k">Decision</div><div class="v ${r.irrigate ? "good" : "bad"}">${r.decision}</div></div>
          <div class="kv"><div class="k">Threshold</div><div class="v">${r.threshold}</div></div>
        </div>
      `;
    } catch (err) {
      out.innerHTML = `<div class="muted">Error: ${String(err.message || err)}</div>`;
    }
  });
}

let espChart;

function initChart() {
  const ctx = document.getElementById("esp32Chart").getContext("2d");

  espChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: [],
      datasets: [
        {
          label: "Temperature (°C)",
          data: [],
          borderWidth: 2
        },
        {
          label: "Humidity (%)",
          data: [],
          borderWidth: 2
        }
      ]
    },
    options: {
      responsive: true,
      animation: false
    }
  });
}


async function manualFetch() {
  try {
    const res = await fetch("/api/esp32/latest", { cache: "no-store" });
    const res_his= await fetch("/api/esp32/history", { cache: "no-store" });
    const data = await res.json();
    const his= await res_his.json();

    const latest = data.latest;
    if (!latest) return;

    // Update UI (reuse your existing logic)
    $("esp32Soil").textContent = Number(latest.soil).toFixed(1);
    $("esp32Received").textContent = fmtTime(latest.received_at_unix);
    $("esp32Temp").textContent = Number(latest.temperature).toFixed(1);
    $("esp32Hum").textContent = Number(latest.humidity).toFixed(1);
    $("esp32Prob").textContent = Number(latest.probability).toFixed(4);
    setDecision($("esp32Decision"), latest.decision);

    // ✅ Clear old graph
    espChart.data.labels = [];
    espChart.data.datasets[0].data = [];
    espChart.data.datasets[1].data = [];

    // ✅ Fill from history
    if (!his.history) return;
    his.history.forEach(item => {
      const time = new Date(item.received_at_unix * 1000).toLocaleTimeString();

      espChart.data.labels.push(time);
      espChart.data.datasets[0].data.push(item.temperature);
      espChart.data.datasets[1].data.push(item.humidity);
    });

    // Update graph
    espChart.update();

  } catch (err) {
    console.error(err);
  }
}

checkHealth();
wireTabs();
wireManualForm();

refreshLatestEsp32();
initChart();

