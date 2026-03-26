const state = {
  uploadedResumeIds: [],
  results: [],
  jobRule: null,
  jobRuleDocument: "",
};

async function request(url, options = {}) {
  const response = await fetch(url, options);
  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const message =
      typeof data === "string" ? data : data.detail || data.message || "请求失败";
    throw new Error(message);
  }

  return data;
}

async function loadHealth() {
  try {
    await request("/health");
    document.getElementById("healthStatus").textContent = "服务正常";
  } catch (error) {
    document.getElementById("healthStatus").textContent = "服务异常";
  }
}

async function loadRule() {
  const result = await request("/api/v1/job-rule");
  const rule = result.data;
  state.jobRule = rule;

  document.getElementById("ruleCard").innerHTML = `
    <div class="rule-grid">
      <div>
        <div class="detail-label">最低工作年限</div>
        <div>${rule.minYears} 年</div>
      </div>
      <div>
        <div class="detail-label">面试阈值</div>
        <div>建议面试 ${rule.thresholds.interview} / 人工复核 ${rule.thresholds.review}</div>
      </div>
      <div>
        <div class="detail-label">必备技能</div>
        <div class="tag-list">${(rule.mustHaveSkills || []).map(tag).join("")}</div>
      </div>
      <div>
        <div class="detail-label">加分技能</div>
        <div class="tag-list">${(rule.preferredSkills || []).map(tag).join("")}</div>
      </div>
      <div>
        <div class="detail-label">偏好特征</div>
        <div class="tag-list">${(rule.preferredTraits || []).map(tag).join("")}</div>
      </div>
      <div>
        <div class="detail-label">规避特征</div>
        <div class="tag-list">${(rule.avoidedTraits || [])
          .map((item) => `<span class="tag warn">${item}</span>`)
          .join("")}</div>
      </div>
      <div>
        <div class="detail-label">重点关注</div>
        <div class="tag-list">${(rule.customFocus || []).map(tag).join("")}</div>
      </div>
      <div>
        <div class="detail-label">权重</div>
        <div class="detail-label">
          技术匹配 ${rule.weights.techMatch} / 工作年限 ${rule.weights.experienceMatch} / 项目经历 ${rule.weights.projectMatch}
        </div>
        <div class="detail-label">
          后端能力 ${rule.weights.backendCapability} / 稳定性 ${rule.weights.stability} / 简历完整度 ${rule.weights.resumeCompleteness} / 个人偏好匹配 ${rule.weights.preferenceMatch}
        </div>
      </div>
      <div class="wide-field">
        <div class="detail-label">权重说明</div>
        <div class="detail-label"><code>techMatch</code>：核心技术栈命中度，主要看 Java / Spring Boot / MySQL / Redis / MQ / 微服务 等是否匹配</div>
        <div class="detail-label"><code>experienceMatch</code>：工作年限匹配，主要看候选人年限是否达到岗位要求</div>
        <div class="detail-label"><code>projectMatch</code>：项目经历贴近度，主要看项目场景是否接近 Java 后端常见业务</div>
        <div class="detail-label"><code>backendCapability</code>：后端能力信号，主要看数据库、缓存、消息队列、分布式、性能优化等能力</div>
        <div class="detail-label"><code>stability</code>：稳定性，主要看平均任职时长和跳槽频率</div>
        <div class="detail-label"><code>resumeCompleteness</code>：简历完整度，主要看职责、成果、项目描述是否清晰</div>
        <div class="detail-label"><code>preferenceMatch</code>：个人筛选习惯匹配，主要看是否符合你在规则里写的偏好与规避特征</div>
      </div>
    </div>
  `;
}

async function loadRuleDocument() {
  const result = await request("/api/v1/job-rule/document");
  state.jobRuleDocument = result.data.content || "";
  document.getElementById("ruleEditor").value = state.jobRuleDocument;
}

async function saveRule(event) {
  event.preventDefault();

  await request("/api/v1/job-rule/document", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      content: document.getElementById("ruleEditor").value,
    }),
  });

  showMessage("ruleMessage", "规则已保存");
  toggleRuleForm(false);
  await loadRule();
  await loadRuleDocument();
}

async function uploadResumes(event) {
  event.preventDefault();
  const files = document.getElementById("resumeFiles").files;
  if (!files.length) {
    showMessage("uploadMessage", "请先选择简历文件");
    return;
  }

  const formData = new FormData();
  Array.from(files).forEach((file) => formData.append("files", file));

  showMessage("uploadMessage", "上传中...");
  const result = await request("/api/v1/resumes/upload", {
    method: "POST",
    body: formData,
  });

  const items = result.data || [];
  state.uploadedResumeIds = items.map((item) => item.resumeId);
  document.getElementById("resumeIdsInput").value = state.uploadedResumeIds.join(",");

  document.getElementById("uploadedList").innerHTML = items
    .map(
      (item) => `
        <div class="uploaded-item">
          <strong>${item.fileName}</strong>
          <div class="detail-label">
            简历ID：${item.resumeId}，状态：${item.parseStatus}${item.duplicate ? "，检测到相同文件，已复用已有记录" : ""}
          </div>
        </div>
      `
    )
    .join("");

  showMessage("uploadMessage", `上传成功，共 ${items.length} 份`);
}

async function runScreening() {
  const raw = document.getElementById("resumeIdsInput").value.trim();
  if (!raw) {
    showMessage("runMessage", "请先输入或上传简历 ID");
    return;
  }

  const resumeIds = raw
    .split(",")
    .map((item) => Number(item.trim()))
    .filter(Boolean);

  showMessage("runMessage", "筛选执行中...");
  const result = await request("/api/v1/screenings/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ resumeIds }),
  });

  showMessage(
    "runMessage",
    `任务已完成：${result.data.taskId}，成功 ${result.data.success} / ${result.data.total}`
  );
  await loadResults();
}

async function rerunAll() {
  showMessage("runMessage", "正在全量重解析简历...");
  await request("/api/v1/resumes/retry-all", {
    method: "POST",
  });

  showMessage("runMessage", "正在全量重跑筛选...");
  const result = await request("/api/v1/screenings/rerun-all", {
    method: "POST",
  });

  showMessage(
    "runMessage",
    `全量任务已完成：${result.data.taskId}，成功 ${result.data.success} / ${result.data.total}`
  );
  await loadResults();
}

async function loadResults() {
  const result = await request("/api/v1/screenings/results");
  state.results = result.data.list || [];

  if (!state.results.length) {
    document.getElementById("resultsTableWrap").innerHTML =
      "<div class='detail-empty'>暂无筛选结果</div>";
    return;
  }

  document.getElementById("resultsTableWrap").innerHTML = `
    <table>
      <thead>
        <tr>
          <th>简历ID</th>
          <th>姓名</th>
          <th>工作年限</th>
          <th>最近岗位</th>
          <th>技能</th>
          <th>总分</th>
          <th>建议</th>
        </tr>
      </thead>
      <tbody>
        ${state.results
          .map(
            (item) => `
              <tr class="clickable" data-id="${item.screeningId}">
                <td>${item.resumeId}</td>
                <td>${item.name || "-"}</td>
                <td>${item.yearsOfExperience || 0} 年</td>
                <td>${item.latestTitle || "-"}</td>
                <td>${(item.skills || []).slice(0, 4).map(tag).join("")}</td>
                <td><span class="tag score">${item.totalScore}</span></td>
                <td>${recommendationTag(item.recommendation)}</td>
              </tr>
            `
          )
          .join("")}
      </tbody>
    </table>
  `;

  document.querySelectorAll("tr.clickable").forEach((row) => {
    row.addEventListener("click", () => loadDetail(row.dataset.id));
  });
}

async function loadDetail(screeningId) {
  const result = await request(`/api/v1/screenings/results/${screeningId}`);
  const detail = result.data;

  document.getElementById("detailCard").innerHTML = `
    <div class="detail-card">
      <div class="panel-header">
        <h3>${detail.basicInfo.name || "-"} <span class="tag score">${detail.totalScore}</span></h3>
        <a class="ghost-btn link-btn" href="${detail.originalFileUrl}" target="_blank" rel="noopener noreferrer">
          查看原始简历
        </a>
      </div>
      <div class="detail-grid">
        ${detailItem("学历", detail.basicInfo.education)}
        ${detailItem("工作年限", `${detail.basicInfo.yearsOfExperience || 0} 年`)}
        ${detailItem("最近公司", detail.careerInfo.latestCompany)}
        ${detailItem("最近岗位", detail.careerInfo.latestTitle)}
        ${detailItem("提取方式", detail.extractionMethod || "rule")}
      </div>

      ${detail.parseWarning ? `<div class="message">LLM 提取失败，已回退到规则抽取：${detail.parseWarning}</div>` : ""}

      <div class="section-title">技能标签</div>
      <div class="tag-list">${(detail.skills || []).map(tag).join("")}</div>

      <div class="section-title">项目经历</div>
      <ul class="clean">
        ${renderProjects(detail.projects)}
      </ul>

      <div class="metrics-grid">
        ${metric("技术匹配", detail.dimensionScores.techMatch)}
        ${metric("工作年限", detail.dimensionScores.experienceMatch)}
        ${metric("项目经历", detail.dimensionScores.projectMatch)}
        ${metric("后端能力", detail.dimensionScores.backendCapability)}
        ${metric("稳定性", detail.dimensionScores.stability)}
        ${metric("简历完整度", detail.dimensionScores.resumeCompleteness)}
      </div>

      <div class="section-title">命中项</div>
      <div class="tag-list">${(detail.matchedPoints || []).map((item) => `<span class="tag">${item}</span>`).join("") || "<span class='detail-label'>暂无</span>"}</div>

      <div class="section-title">风险项</div>
      <div class="tag-list">${(detail.riskPoints || []).map((item) => `<span class="tag warn">${item}</span>`).join("") || "<span class='detail-label'>暂无明显风险</span>"}</div>

      <div class="section-title">系统建议</div>
      <p>${detail.reasonSummary || "-"}</p>

      <div class="section-title">建议面试关注点</div>
      <ul class="clean">
        ${(detail.interviewFocus || []).map((item) => `<li>${item}</li>`).join("") || "<li>暂无</li>"}
      </ul>
    </div>
  `;
}

function toggleRuleForm(show) {
  document.getElementById("ruleForm").classList.toggle("hidden", !show);
}

function showMessage(id, text) {
  document.getElementById(id).textContent = text;
}

function tag(text) {
  return `<span class="tag">${text}</span>`;
}

function recommendationTag(value) {
  const mapping = {
    INTERVIEW: "<span class='tag'>建议面试</span>",
    REVIEW: "<span class='tag score'>人工复核</span>",
    REJECT: "<span class='tag warn'>暂不建议</span>",
  };
  return mapping[value] || value || "-";
}

function detailItem(label, value) {
  return `
    <div class="detail-item">
      <span class="detail-label">${label}</span>
      <strong>${value || "-"}</strong>
    </div>
  `;
}

function metric(label, value) {
  return `
    <div class="metric-card">
      <div class="metric-label">${label}</div>
      <div class="metric-value">${value ?? 0}</div>
    </div>
  `;
}

function renderProjects(projects) {
  if (!projects || !projects.length) {
    return "<li>暂无项目经历</li>";
  }

  return projects
    .map((item) => `<li><strong>${item.name || "项目"}</strong>${item.summary ? `：${item.summary}` : ""}</li>`)
    .join("");
}

document.getElementById("uploadForm").addEventListener("submit", (event) => {
  uploadResumes(event).catch((error) => showMessage("uploadMessage", error.message));
});

document.getElementById("runBtn").addEventListener("click", () => {
  runScreening().catch((error) => showMessage("runMessage", error.message));
});

document.getElementById("loadResultsBtn").addEventListener("click", () => {
  loadResults().catch((error) => showMessage("runMessage", error.message));
});

document.getElementById("rerunAllBtn").addEventListener("click", () => {
  rerunAll().catch((error) => showMessage("runMessage", error.message));
});

document.getElementById("refreshRuleBtn").addEventListener("click", () => {
  loadRule().catch((error) => showMessage("runMessage", error.message));
});

document.getElementById("editRuleBtn").addEventListener("click", () => {
  toggleRuleForm(true);
  loadRuleDocument().catch((error) => showMessage("ruleMessage", error.message));
});

document.getElementById("cancelRuleBtn").addEventListener("click", () => {
  toggleRuleForm(false);
});

document.getElementById("ruleForm").addEventListener("submit", (event) => {
  saveRule(event).catch((error) => showMessage("ruleMessage", error.message));
});

document.getElementById("useSampleBtn").addEventListener("click", () => {
  showMessage("uploadMessage", "示例简历路径：data/sample_resume_java.txt。可直接在页面选择它上传。");
});

loadHealth();
loadRule().catch((error) => showMessage("runMessage", error.message));
loadRuleDocument().catch(() => {});
loadResults().catch(() => {});
