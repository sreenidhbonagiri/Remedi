const FPL = {
  contiguous: { bases: [15960, 21640, 27320, 33000, 38680, 44360, 50040, 55720], inc: 5680 },
  AK: { bases: [19950, 27050, 34150, 41250, 48350, 55450, 62550, 69650], inc: 7100 },
  HI: { bases: [18360, 24890, 31420, 37950, 44480, 51010, 57540, 64070], inc: 6530 },
};

const STATES = [
  "AL","AK","AZ","AR","CA","CO","CT","DC","DE","FL","GA","HI","IA","ID","IL","IN","KS","KY",
  "LA","MA","MD","ME","MI","MN","MO","MS","MT","NC","ND","NE","NH","NJ","NM","NV","NY","OH",
  "OK","OR","PA","RI","SC","SD","TN","TX","UT","VA","VT","WA","WI","WV","WY",
];

const stateSelect = document.getElementById("state");
STATES.forEach((code) => {
  const opt = document.createElement("option");
  opt.value = code;
  opt.textContent = code;
  if (code === "IL") opt.selected = true;
  stateSelect.appendChild(opt);
});

let programs = [];

function regionFor(state) {
  if (state === "AK") return "AK";
  if (state === "HI") return "HI";
  return "contiguous";
}

function povertyGuideline(size, state) {
  const table = FPL[regionFor(state)];
  const n = Math.max(1, Number(size) || 1);
  if (n <= 8) return table.bases[n - 1];
  return table.bases[7] + (n - 8) * table.inc;
}

function money(n) {
  return n.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
}

function selectedProgram() {
  return programs.find((p) => p.name === document.getElementById("program_name").value);
}

function refreshMedications() {
  const program = selectedProgram();
  const medSelect = document.getElementById("medication_name");
  medSelect.innerHTML = "";
  if (!program) {
    medSelect.innerHTML = '<option value="">Select a program first</option>';
    return;
  }
  program.medications.forEach((med, i) => {
    const opt = document.createElement("option");
    opt.value = med.name;
    opt.textContent = `${med.name} · ${med.strength}`;
    if (i === 0) opt.selected = true;
    medSelect.appendChild(opt);
  });
}

function refreshEligibility() {
  const income = Number(document.getElementById("annual_income").value);
  const size = Number(document.getElementById("household_size").value) || 1;
  const state = document.getElementById("state").value;
  const program = selectedProgram();
  const cap = program ? program.fpl_limit_percent : 400;
  const guideline = povertyGuideline(size, state);
  document.getElementById("fpl-base").textContent = money(guideline);
  document.getElementById("fpl-cap").textContent = `${cap}%  (${money(guideline * cap / 100)})`;

  const verdict = document.getElementById("fpl-verdict");
  const pctEl = document.getElementById("fpl-pct");
  if (!Number.isFinite(income) || income < 0 || document.getElementById("annual_income").value === "") {
    pctEl.textContent = "—";
    verdict.textContent = "Enter income to calculate";
    verdict.className = "";
    return;
  }
  const pct = Math.round((income / guideline) * 1000) / 10;
  pctEl.textContent = `${pct}% FPL`;
  if (pct <= cap) {
    verdict.textContent = `Meets ≤ ${cap}% threshold`;
    verdict.className = "pass";
  } else {
    verdict.textContent = `Exceeds ${cap}% program limit`;
    verdict.className = "fail";
  }
}

async function loadPrograms() {
  const select = document.getElementById("program_name");
  try {
    const res = await fetch("/api/v1/programs");
    if (!res.ok) throw new Error("Could not load programs");
    programs = await res.json();
    select.innerHTML = "";
    programs.forEach((program) => {
      const opt = document.createElement("option");
      opt.value = program.name;
      opt.textContent = `${program.name} (${program.manufacturer})`;
      select.appendChild(opt);
    });
    refreshMedications();
    refreshEligibility();
  } catch (err) {
    select.innerHTML = '<option value="">Unable to load programs</option>';
    setStatus(err.message, true);
  }
}

function setStatus(message, isError = false) {
  const el = document.getElementById("status");
  el.textContent = message;
  el.className = "status " + (isError ? "error" : "ok");
}

document.getElementById("program_name").addEventListener("change", () => {
  refreshMedications();
  refreshEligibility();
});
["annual_income", "household_size", "state"].forEach((id) => {
  document.getElementById(id).addEventListener("input", refreshEligibility);
  document.getElementById(id).addEventListener("change", refreshEligibility);
});

document.getElementById("app-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const btn = document.getElementById("submit-btn");
  btn.disabled = true;
  setStatus("Generating PDF…");
  const body = {
    patient_name: document.getElementById("patient_name").value.trim(),
    medication_name: document.getElementById("medication_name").value,
    annual_income: Number(document.getElementById("annual_income").value),
    household_size: Number(document.getElementById("household_size").value),
    state: document.getElementById("state").value,
    is_uninsured: document.getElementById("is_uninsured").checked,
    program_name: document.getElementById("program_name").value,
  };
  try {
    const res = await fetch("/api/v1/applications/generate-pdf", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      let detail = `Request failed (${res.status})`;
      try {
        const payload = await res.json();
        detail = payload.detail || detail;
      } catch {
        /* ignore */
      }
      throw new Error(detail);
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "assistance_application.pdf";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    setStatus("Application PDF downloaded.");
  } catch (err) {
    setStatus(err.message, true);
  } finally {
    btn.disabled = false;
  }
});

loadPrograms();
