// ===== CONFIG =====
const KEYWORDS = [
  "đất đai",
  "quyền sử dụng đất",
  "đất nông nghiệp",
  "địa chính",
  "quy hoạch đất",
  "giải phóng mặt bằng",
  "bồi thường",
  "thu hồi đất",
  "cấp giấy chứng nhận",
  "nông nghiệp",
  "nông thôn",
  "trồng trọt",
  "chăn nuôi",
  "thủy sản",
  "lâm nghiệp",
  "đất ở",
  "đất trồng",
  "tái định cư",
  "đăng ký đất",
  "sổ đỏ",
  "sổ hồng",
  "quy hoạch",
  "sử dụng đất",
  "đất rừng",
  "hoa màu",
  "canh tác",
];

// ===== STATE =====
let ALL_DOCS = []; // all fetched + filtered API docs
let DISPLAY_DOCS = []; // current visible docs
let currentDocTab = "all",
  currentTag = "all",
  currentSearch = "",
  currentYear = "all";
let currentPage = 1;
const PAGE_SIZE = 15;
let DATA_LOCAL = null; // local data.json for map/sidebar

// ===== BOOT =====
fetch("data/metadata.json")
  .then((r) => r.json())
  .then((d) => {
    DATA_LOCAL = d;
    ALL_DOCS = d.vanban || [];
    populateYearFilter();
    renderSidebarStatic();
    renderStats();
    renderNotifyFromAPI();
    renderHotListFromAPI();
    applyFilters();
  })
  .catch((e) => console.error(e));

// ===== STATIC SIDEBAR FROM LOCAL DATA =====
function renderSidebarStatic() {
  document.getElementById("linhVucList").innerHTML = DATA_LOCAL.linhVuc
    .map(
      (lv) =>
        `<li><a href="#" onclick="filterByTag('${lv.ten.toLowerCase()}');return false">${lv.icon} ${lv.ten}</a></li>`,
    )
    .join("");
}

function renderStats() {
  const s = DATA_LOCAL.thongKe;
  document.getElementById("statsList").innerHTML = `
    <li><span>Văn bản pháp luật</span><span class="count">${s.tongVanBan.toLocaleString()}</span></li>
    <li><span>Văn bản đất đai</span><span class="count">${s.vanBanDatDai}</span></li>
    <li><span>Văn bản nông nghiệp</span><span class="count">${s.vanBanNongNghiep}</span></li>
    <li><span>Văn bản địa chính</span><span class="count">${s.vanBanDiaChinh}</span></li>
    <li><span>Còn hiệu lực</span><span class="count">${s.vanBanConHieuLuc}</span></li>
    <li><span>Hết hiệu lực</span><span class="count">${s.vanBanHetHieuLuc}</span></li>`;
}

// (Removed API fetch logic, using data.json directly)

// ===== NOTIFY from API =====
function renderNotifyFromAPI() {
  const el = document.getElementById("notifyList");
  if (!el) return;
  const recent = ALL_DOCS.slice(0, 5);
  if (!recent.length) return;
  el.innerHTML = recent
    .map(
      (d) =>
        `<div class="notify-item">
      <a href="#" onclick="openDetail('${d.id}');return false">${d.tieuDe.substring(0, 80)}...</a>
      <span class="time"> (${d.ngayBanHanh})</span>
    </div>`,
    )
    .join("");
}

// ===== HOT LIST from API =====
function renderHotListFromAPI() {
  const el = document.getElementById("hotList");
  if (!el) return;
  const top = ALL_DOCS.slice(0, 5);
  if (!top.length) return;
  el.innerHTML = top
    .map(
      (d, i) =>
        `<li><a href="#" onclick="openDetail('${d.id}');return false">${d.soHieu} - ${d.loaiVanBan}</a>
     <span class="views">(${Math.floor(Math.random() * 3000 + 500).toLocaleString()} lượt)</span></li>`,
    )
    .join("");
}

// ===== RENDER DOCS =====
function renderDocs(docs) {
  DISPLAY_DOCS = docs;
  const total = docs.length;
  const totalPages = Math.ceil(total / PAGE_SIZE);
  if (currentPage > totalPages) currentPage = 1;
  const start = (currentPage - 1) * PAGE_SIZE;
  const page = docs.slice(start, start + PAGE_SIZE);

  document.getElementById("docCount").textContent =
    `${total} văn bản (trang ${currentPage}/${totalPages || 1})`;

  if (!docs.length) {
    document.getElementById("docList").innerHTML =
      `<div style="padding:30px;text-align:center;color:#999">
        <div style="font-size:40px;margin-bottom:10px">📭</div>
        Không tìm thấy văn bản phù hợp.
        <a href="#" onclick="resetFilter();return false" style="display:block;margin-top:8px">← Xem tất cả</a>
      </div>`;
    return;
  }

  document.getElementById("docList").innerHTML = page
    .map(
      (doc) => `
    <div class="doc-item">
      <div class="doc-title-row">
        <a href="#" onclick="openDetail('${doc.id}');return false" class="doc-title">${doc.tieuDe || "(Không có tiêu đề)"}</a>
        ${doc.tinhTrang === "Còn hiệu lực" ? '<span class="badge-hot">MỚI</span>' : ""}
      </div>
      <div class="doc-links">
        <a href="#" onclick="openDetail('${doc.id}');return false">Xem nội dung</a>
        <a href="${doc.url}" target="_blank">Văn bản gốc</a>
        <a href="#">Tải về</a>
      </div>
      <div class="doc-info-row">
        <span><span class="label">Số hiệu:</span> <strong>${doc.soHieu}</strong></span>
        <span><span class="label">Loại:</span> ${doc.loaiVanBan}</span>
        <span><span class="label">Cơ quan:</span> ${doc.coQuanBanHanh}</span>
        <span><span class="label">Ban hành:</span> ${doc.ngayBanHanh}</span>
        <span><span class="label">Hiệu lực:</span> ${doc.ngayHieuLuc}</span>
        <span>Tình trạng: <span class="doc-status-badge ${doc.tinhTrang === "Còn hiệu lực" ? "hl" : "hhl"}">${doc.tinhTrang}</span></span>
        ${doc.nganh ? `<span><span class="label">Ngành:</span> ${doc.nganh}</span>` : ""}
      </div>
    </div>
  `,
    )
    .join("");

  // Pagination
  const pag = [];
  if (totalPages > 1) {
    pag.push(
      `<div class="pagination" style="padding:12px;display:flex;gap:6px;justify-content:center;border-top:1px solid #eee">`,
    );
    if (currentPage > 1)
      pag.push(
        `<button onclick="goPage(${currentPage - 1})" class="pag-btn">← Trước</button>`,
      );
    for (
      let i = Math.max(1, currentPage - 2);
      i <= Math.min(totalPages, currentPage + 2);
      i++
    )
      pag.push(
        `<button onclick="goPage(${i})" class="pag-btn${i === currentPage ? " active" : ""}">${i}</button>`,
      );
    if (currentPage < totalPages)
      pag.push(
        `<button onclick="goPage(${currentPage + 1})" class="pag-btn">Sau →</button>`,
      );
    pag.push(`</div>`);
    document
      .getElementById("docList")
      .insertAdjacentHTML("beforeend", pag.join(""));
  }
}

function goPage(p) {
  currentPage = p;
  renderDocs(DISPLAY_DOCS);
  window.scrollTo(0, 400);
}

// ===== OPEN DETAIL PAGE =====
function openDetail(id) {
  window.location.href = "detail.html?id=" + encodeURIComponent(id);
}

// ===== MODAL DETAIL (quick preview) =====
function openDetailModal(id) {
  const doc = ALL_DOCS.find((d) => d.id == id);
  if (!doc) return;
  document.getElementById("modalTitle").textContent = doc.tieuDe;
  document.getElementById("modalMeta").innerHTML = `
    <div class="modal-meta-item"><div class="label">Số hiệu</div><div class="value">${doc.soHieu}</div></div>
    <div class="modal-meta-item"><div class="label">Loại văn bản</div><div class="value">${doc.loaiVanBan}</div></div>
    <div class="modal-meta-item"><div class="label">Cơ quan</div><div class="value">${doc.coQuanBanHanh}</div></div>
    <div class="modal-meta-item"><div class="label">Ngày ban hành</div><div class="value">${doc.ngayBanHanh}</div></div>
    <div class="modal-meta-item"><div class="label">Ngày hiệu lực</div><div class="value">${doc.ngayHieuLuc}</div></div>
    <div class="modal-meta-item"><div class="label">Tình trạng</div>
      <div class="value" style="color:${doc.tinhTrang === "Còn hiệu lực" ? "#137333" : "#c5221f"}">${doc.tinhTrang}</div></div>`;
  
  // Show loading spinner for content
  document.getElementById("modalContent").innerHTML = `
    <div style="text-align:center;padding:40px 20px;color:#999">
      <div style="font-size:32px;animation:spin 1.2s linear infinite;display:inline-block;margin-bottom:10px">⏳</div>
      <div>Đang tải nội dung văn bản...</div>
    </div>
  `;
  document.getElementById("modalRelated").innerHTML = "";
  document.getElementById("modalOverlay").classList.add("show");
  document.body.style.overflow = "hidden";

  // Lazy load the full article JSON
  fetch(`articles/${id}.json`)
    .then(r => {
      if (!r.ok) throw new Error("Không thể tải tập tin.");
      return r.json();
    })
    .then(fullDoc => {
      const content = fullDoc.noiDung || "";
      const isHtml = content.includes('<div') || content.includes('<p') || content.includes('<table');
      
      const contentHtml = isHtml 
        ? `<div class="doc-content">${content}</div>` 
        : `<div style="white-space:pre-wrap;font-size:12px;line-height:1.8;color:#333">${content.substring(0, 3000)}${content.length > 3000 ? "\n\n..." : ""}</div>`;
        
      document.getElementById("modalContent").innerHTML = `
        ${contentHtml}
        <div style="margin-top:16px;text-align:center">
          <a href="${fullDoc.url}" target="_blank" style="padding:8px 20px;background:#cc0000;color:#fff;border-radius:4px;text-decoration:none;font-size:13px">
            📖 Xem toàn văn tại vbpl.vn
          </a>
        </div>
      `;
    })
    .catch(err => {
      document.getElementById("modalContent").innerHTML = `
        <div style="color:#c00;padding:20px;text-align:center">
          ⚠️ Không thể tải nội dung văn bản. Vui lòng xem toàn văn trực tiếp tại VBPL.
        </div>
        <div style="margin-top:16px;text-align:center">
          <a href="${doc.url || '#'}" target="_blank" style="padding:8px 20px;background:#cc0000;color:#fff;border-radius:4px;text-decoration:none;font-size:13px">
            📖 Xem toàn văn tại vbpl.vn
          </a>
        </div>
      `;
    });
}
function closeModal(e) {
  if (!e || e.target === document.getElementById("modalOverlay")) {
    document.getElementById("modalOverlay").classList.remove("show");
    document.body.style.overflow = "";
  }
}

// ===== FILTERS =====
function filterByTag(tag) {
  currentTag = tag;
  currentPage = 1;
  applyFilters();
}
function setDocFilterType(type) {
  currentDocTab = type;
  currentPage = 1;

  document.querySelectorAll(".search-tabs button").forEach((b) => {
    b.classList.remove("active");
    if (
      b.textContent === type ||
      (type === "all" && b.textContent === "Văn bản Pháp Luật")
    ) {
      b.classList.add("active");
    }
  });

  document.querySelectorAll(".doc-tabs button").forEach((b) => {
    b.classList.remove("active");
    if (
      b.textContent === type ||
      (type === "all" && b.textContent === "Tất cả")
    ) {
      b.classList.add("active");
    }
  });

  applyFilters();
}

function switchDocTab(type) {
  setDocFilterType(type);
}
function switchSearchTab(type) {
  setDocFilterType(type);
}
function extractYear(ngayBanHanh) {
  if (!ngayBanHanh || ngayBanHanh === "—") return null;
  const parts = ngayBanHanh.split("/");
  if (parts.length === 3) {
    const y = parts[2].trim();
    if (/^\d{4}$/.test(y)) return y;
  }
  const match = ngayBanHanh.match(/\b(19|20)\d{2}\b/);
  if (match) return match[0];
  return null;
}

function populateYearFilter() {
  const selectEl = document.getElementById("yearFilter");
  if (!selectEl) return;
  const currentYearNum = new Date().getFullYear();
  let minYear = currentYearNum - 10; // mặc định 10 năm trước
  ALL_DOCS.forEach((d) => {
    const y = parseInt(extractYear(d.ngayBanHanh));
    if (y && y > 1900 && y <= currentYearNum) {
      if (y < minYear) minYear = y;
    }
  });
  let html = `<option value="all">Tất cả năm</option>`;
  for (let y = currentYearNum; y >= minYear; y--) {
    html += `<option value="${y}">Năm ${y}</option>`;
  }
  selectEl.innerHTML = html;
}

function changeYearFilter() {
  const selectEl = document.getElementById("yearFilter");
  if (selectEl) {
    currentYear = selectEl.value;
    currentPage = 1;
    applyFilters();
  }
}

function doSearch() {
  currentSearch = document.getElementById("searchInput").value;
  const selectEl = document.getElementById("yearFilter");
  if (selectEl) {
    currentYear = selectEl.value;
  }
  currentPage = 1;
  applyFilters();
}
function quickSearch(val) {
  document.getElementById("searchInput").value = val;
  doSearch();
}
function applyFilters() {
  const kw = (currentSearch || "").toLowerCase().trim();
  let docs = ALL_DOCS;
  if (currentTag && currentTag !== "all")
    docs = docs.filter((d) =>
      ((d.tieuDe || "") + (d.nganh || "") + (d.linhVuc || ""))
        .toLowerCase()
        .includes(currentTag.toLowerCase()),
    );
  if (currentDocTab && currentDocTab !== "all")
    docs = docs.filter((d) => d.loaiVanBan === currentDocTab);
  if (currentYear && currentYear !== "all")
    docs = docs.filter((d) => extractYear(d.ngayBanHanh) === currentYear);
  if (kw)
    docs = docs.filter(
      (d) =>
        (d.tieuDe && d.tieuDe.toLowerCase().includes(kw)) ||
        (d.soHieu && d.soHieu.toLowerCase().includes(kw)) ||
        (d.coQuanBanHanh && d.coQuanBanHanh.toLowerCase().includes(kw))
    );
  renderDocs(docs);
}
function resetFilter() {
  currentTag = "all";
  currentSearch = "";
  currentYear = "all";
  document.getElementById("searchInput").value = "";
  const selectEl = document.getElementById("yearFilter");
  if (selectEl) selectEl.value = "all";
  setDocFilterType("all");
}

// ===== TABS =====
function showTab(tab) {
  document.getElementById("tab-vanban").style.display =
    tab === "vanban" ? "block" : "none";
  document.getElementById("tab-map").style.display =
    tab === "map" ? "block" : "none";
}

// ===== KEYBOARD =====
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeModal();
  if (e.key === "Enter" && document.activeElement.id === "searchInput")
    doSearch();
});
