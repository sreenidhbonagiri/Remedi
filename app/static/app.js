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
  pctEl.textContent = `${pct}% of the poverty line`;
  if (pct <= cap) {
    verdict.textContent = `Yes — you're within the ${cap}% limit`;
    verdict.className = "pass";
  } else {
    verdict.textContent = `Likely not — this exceeds the ${cap}% limit`;
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
    const frame = document.getElementById("pdf-frame");
    const wrap = document.getElementById("pdf-frame-wrap");
    if (frame.dataset.url) URL.revokeObjectURL(frame.dataset.url);
    frame.src = url;
    frame.dataset.url = url;
    wrap.hidden = false;
    const a = document.createElement("a");
    a.href = url;
    a.download = "assistance_application.pdf";
    document.body.appendChild(a);
    a.click();
    a.remove();
    setStatus("Your free application is ready — preview below, and it's downloaded too.");
  } catch (err) {
    setStatus(err.message, true);
  } finally {
    btn.disabled = false;
  }
});

loadPrograms();

const triageState = document.getElementById("triage_state");
if (triageState) {
  STATES.forEach((code) => {
    const opt = document.createElement("option");
    opt.value = code;
    opt.textContent = code;
    if (code === "PA") opt.selected = true;
    triageState.appendChild(opt);
  });
}

function setTriageStatus(message, isError = false) {
  const el = document.getElementById("triage-status");
  el.textContent = message;
  el.className = "status " + (isError ? "error" : "ok");
}

function moneyCash(n) {
  if (n == null || !Number.isFinite(Number(n))) return "—";
  return Number(n).toLocaleString("en-US", { style: "currency", currency: "USD" });
}

const GENERIC_MATCH_LABEL = "✅ FDA-Approved Generic Equivalent (Same active medicine)";

const EXAMPLE_SCENARIOS = {
  humira: {
    query:
      "I take Humira, and my family of 2 earns about $32,000 a year. We don't have insurance.",
    income: 32000,
    household: 2,
    state: "PA",
    uninsured: true,
    medicare: false,
  },
  eliquis: {
    query: "I take Eliquis. I'm on Medicare and my income is about $28,000 a year.",
    income: 28000,
    household: 1,
    state: "PA",
    uninsured: false,
    medicare: true,
  },
};

document.querySelectorAll(".example-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    const example = EXAMPLE_SCENARIOS[btn.dataset.example];
    if (!example) return;
    document.getElementById("triage_query").value = example.query;
    document.getElementById("triage_income").value = example.income;
    document.getElementById("triage_household").value = example.household;
    const triageStateSelect = document.getElementById("triage_state");
    if (triageStateSelect) triageStateSelect.value = example.state;
    document.getElementById("triage_uninsured").checked = example.uninsured;
    document.getElementById("triage_medicare").checked = example.medicare;
    setTriageStatus("Example filled in — click \u201cCheck My Options\u201d whenever you're ready.");
  });
});

document.getElementById("triage-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const btn = document.getElementById("triage-btn");
  const empty = document.getElementById("triage-empty");
  const errorEl = document.getElementById("triage-error");
  const planEl = document.getElementById("triage-plan");
  const altsWrap = document.getElementById("triage-alts");
  const banner = document.getElementById("triage-savings-banner");
  btn.disabled = true;
  errorEl.hidden = true;
  banner.hidden = true;
  setTriageStatus("Checking your options…");
  const incomeRaw = document.getElementById("triage_income").value;
  const body = {
    query: document.getElementById("triage_query").value.trim(),
    household_size: Number(document.getElementById("triage_household").value) || 1,
    state: document.getElementById("triage_state").value,
    is_uninsured: document.getElementById("triage_uninsured").checked,
    is_medicare: document.getElementById("triage_medicare").checked,
  };
  if (incomeRaw !== "") body.annual_income = Number(incomeRaw);
  try {
    const res = await fetch("/api/v1/agent/triage", {
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
    const payload = await res.json();
    empty.hidden = true;
    planEl.hidden = false;
    planEl.textContent = payload.action_plan || "We couldn't put together a plan this time — please try again.";
    const alts = (payload.savings && payload.savings.alternatives) || [];
    const tbody = document.getElementById("triage-alts-body");
    tbody.innerHTML = "";
    if (!alts.length) {
      altsWrap.hidden = true;
    } else {
      altsWrap.hidden = false;
      alts.forEach((alt) => {
        const tr = document.createElement("tr");
        const save =
          alt.savings_percent == null
            ? "—"
            : `${moneyCash(alt.savings_amount)} (${alt.savings_percent}% off)`;
        const genericMatch = alt.te_code ? GENERIC_MATCH_LABEL : "—";
        tr.innerHTML = `<td>${alt.name}</td><td>${genericMatch}</td><td>${moneyCash(alt.cash_price)}</td><td>${save}</td>`;
        tbody.appendChild(tr);
      });
      const top = alts[0];
      if (top && top.savings_amount != null && top.savings_percent != null) {
        banner.hidden = false;
        banner.textContent = `You could save ${moneyCash(top.savings_amount)} (${top.savings_percent}% off) by asking about ${top.name}.`;
      }
    }
    setTriageStatus("Here's what we found — every number below comes from real pricing and eligibility data.");
  } catch (err) {
    empty.hidden = true;
    planEl.hidden = true;
    altsWrap.hidden = true;
    banner.hidden = true;
    errorEl.hidden = false;
    errorEl.textContent = err.message || "We couldn't check your options this time — please try again.";
    setTriageStatus(err.message, true);
  } finally {
    btn.disabled = false;
  }
});

