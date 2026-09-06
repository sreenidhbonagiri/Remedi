const STATES = [
  "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DC", "DE", "FL", "GA", "HI", "IA", "ID", "IL", "IN", "KS", "KY",
  "LA", "MA", "MD", "ME", "MI", "MN", "MO", "MS", "MT", "NC", "ND", "NE", "NH", "NJ", "NM", "NV", "NY", "OH",
  "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VA", "VT", "WA", "WI", "WV", "WY",
];

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

function moneyCash(n) {
  if (n == null || !Number.isFinite(Number(n))) return "—";
  return Number(n).toLocaleString("en-US", { style: "currency", currency: "USD" });
}

function setTriageStatus(message, isError = false) {
  const el = document.getElementById("triage-status");
  el.textContent = message;
  el.className = "status " + (isError ? "error" : "ok");
}

function setApplyStatus(message, isError = false) {
  const el = document.getElementById("apply-status");
  el.textContent = message;
  el.className = "status " + (isError ? "error" : "ok");
}

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
    if (triageState) triageState.value = example.state;
    document.getElementById("triage_uninsured").checked = example.uninsured;
    document.getElementById("triage_medicare").checked = example.medicare;
    setTriageStatus("Example filled in — click \u201cAsk Remy\u201d whenever you're ready.");
  });
});

// Populated after a successful triage response; used to pre-fill the free
// application download without asking the patient to re-enter everything.
let applicationContext = null;

// Follow-up chat: a random per-page-load session id, plus the triage context
// (savings/fpl/medication_query) Remy needs to answer questions grounded in
// real numbers instead of guessing.
const chatSessionId =
  (window.crypto && window.crypto.randomUUID && window.crypto.randomUUID()) ||
  `session-${Date.now()}-${Math.random().toString(16).slice(2)}`;
let chatContext = null;
let chatHasContext = false;

function appendChatBubble(role, text) {
  const messages = document.getElementById("chat-messages");
  const empty = messages.querySelector(".chat-empty");
  if (empty) empty.remove();
  const row = document.createElement("div");
  row.className = `chat-row ${role}`;
  if (role === "remy") {
    row.innerHTML = `
      <span class="remy-bot remy-bot-sm" aria-hidden="true">
        <svg viewBox="0 0 120 120" class="remy-bot-svg">
          <rect x="18" y="22" width="84" height="78" rx="26" class="remy-head" />
          <circle cx="36" cy="66" r="7" class="remy-cheek" />
          <circle cx="84" cy="66" r="7" class="remy-cheek" />
          <path d="M40 52 Q47 43 54 52" class="remy-eye" />
          <path d="M66 52 Q73 43 80 52" class="remy-eye" />
          <path d="M46 76 Q60 90 74 76" class="remy-mouth" />
          <line x1="60" y1="22" x2="60" y2="6" class="remy-antenna-stem" />
          <circle cx="60" cy="6" r="5" class="remy-antenna-dot" />
        </svg>
      </span>
      <div class="chat-bubble"></div>
    `;
  } else {
    row.innerHTML = `<div class="chat-bubble"></div>`;
  }
  row.querySelector(".chat-bubble").textContent = text;
  messages.appendChild(row);
  messages.scrollTop = messages.scrollHeight;
}

function renderPayingSection(medicationLabel, brandPrice) {
  const el = document.getElementById("result-paying");
  if (brandPrice != null) {
    el.textContent = `Right now, ${medicationLabel} typically costs ${moneyCash(brandPrice)} in cash price.`;
  } else {
    el.textContent = `We don't have a cash price on file yet for ${medicationLabel}.`;
  }
}

function renderGenericSection(medicationLabel, brandPrice, alternatives) {
  const el = document.getElementById("result-generic");
  const banner = document.getElementById("triage-savings-banner");
  if (!alternatives.length) {
    el.innerHTML =
      "<p>We don't have a lower-cost generic on file for this medication yet — ask your pharmacist if one is available.</p>";
    banner.hidden = true;
    return;
  }
  const alt = alternatives[0];
  const parts = [
    `<p>Good news — <strong>${alt.name}</strong> has the exact same active ingredient as ${medicationLabel}. It typically costs ${moneyCash(alt.cash_price)} instead of ${moneyCash(alt.brand_cash_price ?? brandPrice)}.</p>`,
  ];
  if (alt.savings_amount != null && alt.savings_percent != null) {
    parts.push(
      `<p><strong>That's ${moneyCash(alt.savings_amount)} back in your pocket — about ${alt.savings_percent}% off.</strong></p>`
    );
  }
  parts.push(
    `<p class="ask-line">Try asking: “Is ${alt.name} a safe generic option for me instead of ${medicationLabel}?”</p>`
  );
  el.innerHTML = parts.join("");

  if (alt.savings_amount != null && alt.savings_percent != null) {
    banner.hidden = false;
    banner.textContent = `You could save ${moneyCash(alt.savings_amount)} a year (${alt.savings_percent}% off) by asking about ${alt.name}.`;
  } else {
    banner.hidden = true;
  }
}

function renderProgramSection(programs) {
  const el = document.getElementById("result-program");
  if (!programs.length) {
    el.innerHTML = "<p>We don't have a free medicine program on file for this medication yet.</p>";
    return null;
  }
  const eligible = programs.find((p) => p.eligible === true);
  const chosen = eligible || programs[0];
  let pillClass = "status-unscored";
  let pillText = "Add your income to check";
  let detail = "";
  if (chosen.eligible === true) {
    pillClass = "status-eligible";
    pillText = "You likely qualify";
    detail = `<p>${chosen.name} (${chosen.manufacturer}) accepts households up to ${chosen.fpl_limit_percent}% of the poverty line, and your household is at ${chosen.fpl_percent}% — so you're in range. Call ${chosen.phone} with any questions.</p>`;
  } else if (chosen.eligible === false) {
    pillClass = "status-not-eligible";
    pillText = "Not likely eligible right now";
    detail = `<p>${chosen.reason}</p>`;
  } else {
    detail = `<p>Add your income and household size above so we can check ${chosen.name}'s income limit for you.</p>`;
  }
  el.innerHTML = `<span class="status-pill ${pillClass}">${pillText}</span>${detail}`;
  return chosen;
}

document.getElementById("triage-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const btn = document.getElementById("triage-btn");
  const empty = document.getElementById("triage-empty");
  const errorEl = document.getElementById("triage-error");
  const resultsEl = document.getElementById("triage-results");
  const banner = document.getElementById("triage-savings-banner");
  const applicationCard = document.getElementById("application-card");
  btn.disabled = true;
  errorEl.hidden = true;
  banner.hidden = true;
  setTriageStatus("Remy is checking your options…");
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
    const savings = payload.savings || {};
    const fpl = payload.fpl || null;
    const medicationLabel = payload.medication_query || savings.matched_medication || "your medication";

    empty.hidden = true;
    resultsEl.hidden = false;

    renderPayingSection(medicationLabel, savings.brand_cash_price);
    renderGenericSection(medicationLabel, savings.brand_cash_price, savings.alternatives || []);
    const chosenProgram = renderProgramSection(savings.eligible_programs || []);

    const canApply = Boolean(chosenProgram && fpl && savings.matched_medication);
    if (canApply) {
      applicationContext = {
        medication: savings.matched_medication,
        program_name: chosenProgram.name,
        annual_income: fpl.annual_income,
        household_size: fpl.household_size,
        state: fpl.state,
        is_uninsured: body.is_uninsured,
      };
      applicationCard.hidden = false;
    } else {
      applicationContext = null;
      applicationCard.hidden = true;
    }

    chatContext = {
      savings,
      fpl,
      medication_query: medicationLabel,
    };
    chatHasContext = false;
    document.getElementById("chat-card").hidden = false;

    setTriageStatus("Here's what Remy found — every number above comes from real pricing and eligibility data.");
  } catch (err) {
    empty.hidden = true;
    resultsEl.hidden = true;
    banner.hidden = true;
    applicationContext = null;
    applicationCard.hidden = true;
    errorEl.hidden = false;
    errorEl.textContent = err.message || "We couldn't check your options this time — please try again.";
    setTriageStatus(err.message, true);
  } finally {
    btn.disabled = false;
  }
});

document.getElementById("apply-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const btn = document.getElementById("apply-btn");
  const patientName = document.getElementById("apply_patient_name").value.trim();
  if (!patientName) {
    setApplyStatus("Please enter your name first.", true);
    return;
  }
  if (!applicationContext) {
    setApplyStatus("Ask Remy about your medication and income first.", true);
    return;
  }
  btn.disabled = true;
  setApplyStatus("Preparing your application…");
  const body = {
    patient_name: patientName,
    medication_name: applicationContext.medication,
    annual_income: applicationContext.annual_income,
    household_size: applicationContext.household_size,
    state: applicationContext.state,
    is_uninsured: applicationContext.is_uninsured,
    program_name: applicationContext.program_name,
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
    setApplyStatus("Your free application is ready — preview below, and it's downloaded too.");
  } catch (err) {
    setApplyStatus(err.message, true);
  } finally {
    btn.disabled = false;
  }
});

document.getElementById("chat-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const input = document.getElementById("chat_message");
  const sendBtn = document.getElementById("chat-send-btn");
  const typing = document.getElementById("chat-typing");
  const message = input.value.trim();
  if (!message) return;

  appendChatBubble("user", message);
  input.value = "";
  input.disabled = true;
  sendBtn.disabled = true;
  typing.hidden = false;

  const body = { session_id: chatSessionId, message };
  if (!chatHasContext && chatContext) {
    body.context = chatContext;
  }

  try {
    const res = await fetch("/api/v1/agent/chat", {
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
    chatHasContext = true;
    appendChatBubble("remy", payload.reply);
  } catch (err) {
    appendChatBubble(
      "remy",
      `Sorry, I couldn't answer that just now (${err.message || "please try again"}).`
    );
  } finally {
    typing.hidden = true;
    input.disabled = false;
    sendBtn.disabled = false;
    input.focus();
  }
});
