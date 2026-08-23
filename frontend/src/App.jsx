import { useEffect, useState } from "react";
import { getFilterOptions, searchAssets } from "./api";
import { formatArea, formatAuctionDate, formatPrice, googleMapsUrl, matchesArea } from "./formatters";

const INITIAL_FILTERS = {
  province: "", amphur: "", tambon: "",
  raiCondition: "gt", raiValue: "",
  nganCondition: "lt", nganValue: "",
  squareWahCondition: "eq", squareWahValue: "",
};
const PAGE_SIZE = 9;

function Icon({ name }) {
  const paths = {
    list: <path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01" />,
    search: <path d="m21 21-4.35-4.35M19 11a8 8 0 1 1-16 0 8 8 0 0 1 16 0Z" />,
    pin: <path d="M20 10c0 5-8 11-8 11S4 15 4 10a8 8 0 1 1 16 0Zm-8 3a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z" />,
    land: <path d="m3 17 5-5 4 4 3-3 6 6M8 12V5h9v8" />,
    refresh: <path d="M20 11a8 8 0 1 0-2.34 5.66M20 4v7h-7" />,
    filter: <path d="M4 5h16l-6 7v5l-4 2v-7L4 5Z" />,
    calendar: <path d="M6 2v4M18 2v4M3 9h18M5 4h14a2 2 0 0 1 2 2v14H3V6a2 2 0 0 1 2-2Z" />,
  };
  return <svg viewBox="0 0 24 24" aria-hidden="true">{paths[name]}</svg>;
}

function AreaField({ label, condition, value, onCondition, onValue }) {
  return (
    <div className="field area-field">
      <label>{label}</label>
      <div className="area-inputs">
        <select value={condition} onChange={(event) => onCondition(event.target.value)}>
          <option value="gt">มากกว่า</option>
          <option value="lt">น้อยกว่า</option>
          <option value="eq">เท่ากับ</option>
        </select>
        <input type="number" min="0" inputMode="decimal" value={value}
          placeholder="ระบุจำนวน" onChange={(event) => onValue(event.target.value)} />
      </div>
    </div>
  );
}

function AssetCard({ asset }) {
  const mapUrl = googleMapsUrl(asset.location);
  const address = [asset.tambon, asset.amphur, asset.province].filter(Boolean).join(" • ");
  return (
    <article className="asset-card">
      <div className="card-topline">
        <span className="asset-type">{asset.asset_type || "ไม่ระบุประเภท"}</span>
        <span className="case-number">คดี {asset.case_number || "-"}</span>
      </div>
      <div className="price-label">ราคาทรัพย์</div>
      <div className="price">{formatPrice(asset.price_final)}</div>
      <div className="next-auction"><Icon name="calendar" /><span><small>วันประมูลถัดไป</small>{asset.next_auction_date ? <p>ประมูลครั้งที่ {asset.next_auction_round || "-"} <strong>วันที่ {formatAuctionDate(asset.next_auction_date)}</strong></p> : <p>ยังไม่มีวันประมูลถัดไป</p>}</span></div>
      <div className="asset-facts">
        <div><span>ขนาดพื้นที่</span><strong>{formatArea(asset)}</strong></div>
        <div><span>เลขที่โฉนด</span><strong>{asset.deed_number || "-"}</strong></div>
      </div>
      {mapUrl ? (
        <a className="map-link" href={mapUrl} target="_blank" rel="noreferrer">
          <Icon name="pin" /><span><strong>เปิดตำแหน่งบน Google Maps</strong><small>{address || "ไม่พบข้อมูลที่อยู่"}</small></span>
        </a>
      ) : <span className="map-link unavailable"><span><strong>ไม่มีข้อมูลพิกัด</strong><small>{address || "ไม่พบข้อมูลที่อยู่"}</small></span></span>}
    </article>
  );
}

export default function App() {
  const [filters, setFilters] = useState(INITIAL_FILTERS);
  const [provinces, setProvinces] = useState([]);
  const [amphurs, setAmphurs] = useState([]);
  const [tambons, setTambons] = useState([]);
  const [assets, setAssets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filterError, setFilterError] = useState("");
  const [expanded, setExpanded] = useState(true);
  const [page, setPage] = useState(1);
  const update = (key, value) => setFilters((current) => ({ ...current, [key]: value }));

  useEffect(() => {
    const controller = new AbortController();
    getFilterOptions("provinces", {}, controller.signal)
      .then((items) => { setProvinces(items); setFilterError(""); })
      .catch((requestError) => requestError.name !== "AbortError" && setFilterError("โหลดข้อมูลจังหวัดไม่สำเร็จ"));
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!filters.province) { setAmphurs([]); setTambons([]); return undefined; }
    const controller = new AbortController();
    getFilterOptions("amphurs", { province: filters.province }, controller.signal)
      .then((items) => { setAmphurs(items); setFilterError(""); })
      .catch((requestError) => requestError.name !== "AbortError" && setFilterError("โหลดข้อมูลอำเภอไม่สำเร็จ"));
    return () => controller.abort();
  }, [filters.province]);

  useEffect(() => {
    if (!filters.province || !filters.amphur) { setTambons([]); return undefined; }
    const controller = new AbortController();
    getFilterOptions("tambons", { province: filters.province, amphur: filters.amphur }, controller.signal)
      .then((items) => { setTambons(items); setFilterError(""); })
      .catch((requestError) => requestError.name !== "AbortError" && setFilterError("โหลดข้อมูลตำบลไม่สำเร็จ"));
    return () => controller.abort();
  }, [filters.province, filters.amphur]);

  async function runSearch(nextFilters = filters) {
    setLoading(true); setError("");
    try {
      const response = await searchAssets(nextFilters);
      setAssets((response.items || []).filter((asset) => matchesArea(asset, nextFilters)));
      setPage(1);
    } catch { setError("ค้นหาทรัพย์ไม่สำเร็จ กรุณาตรวจสอบว่า Backend กำลังทำงาน"); }
    finally { setLoading(false); }
  }

  useEffect(() => { runSearch(INITIAL_FILTERS); }, []);

  function reset() {
    setFilters(INITIAL_FILTERS); setAmphurs([]); setTambons([]); runSearch(INITIAL_FILTERS);
  }

  const activeCriteria = [
    filters.province && `จังหวัด: ${filters.province}`,
    filters.amphur && `อำเภอ: ${filters.amphur}`,
    filters.tambon && `ตำบล: ${filters.tambon}`,
  ].filter(Boolean);
  const totalPages = Math.max(1, Math.ceil(assets.length / PAGE_SIZE));
  const visibleAssets = assets.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  return (
    <main>
      <header className="hero">
        <div className="brand-mark">HH</div>
        <div><p>HOMEHUB AUCTION</p><h1>ค้นหาทรัพย์ที่ใช่<br />ในข้อมูลที่อ่านง่ายกว่า</h1></div>
        <div className="hero-note">ข้อมูลทรัพย์ขายทอดตลาด<br /><strong>อัปเดตจากกรมบังคับคดี</strong></div>
      </header>
      <nav className="view-tabs" aria-label="รูปแบบการค้นหา">
        <span className="active"><Icon name="list" />รายการทรัพย์</span>
        <span><Icon name="pin" />พิกัดทรัพย์บนแผนที่</span>
      </nav>
      <section className="search-panel">
        <div className="panel-actions">
          <button className="quiet-button" type="button" onClick={() => setExpanded(!expanded)}>
            <Icon name="filter" />{expanded ? "ซ่อนเงื่อนไขค้นหา" : "แสดงเงื่อนไขค้นหา"}
          </button>
          <button className="reset-button" type="button" onClick={reset}><Icon name="refresh" />ล้างเงื่อนไข</button>
        </div>
        {activeCriteria.length > 0 && <div className="criteria-bar"><strong>เงื่อนไขการค้นหา:</strong>{activeCriteria.map((item) => <span key={item}>{item}</span>)}</div>}
        {filterError && <div className="filter-error">{filterError}</div>}
        {expanded && (
          <form className="filter-grid" onSubmit={(event) => { event.preventDefault(); runSearch(); }}>
            <div className="field"><label htmlFor="province">จังหวัด</label>
              <select id="province" value={filters.province} onChange={(event) => setFilters((current) => ({ ...current, province: event.target.value, amphur: "", tambon: "" }))}>
                <option value="">-- เลือกจังหวัด --</option>{provinces.map((item) => <option key={item}>{item}</option>)}
              </select>
            </div>
            <div className="field"><label htmlFor="amphur">เขต/อำเภอ</label>
              <select id="amphur" value={filters.amphur} disabled={!filters.province} onChange={(event) => setFilters((current) => ({ ...current, amphur: event.target.value, tambon: "" }))}>
                <option value="">-- เลือกอำเภอ --</option>{amphurs.map((item) => <option key={item}>{item}</option>)}
              </select>
            </div>
            <div className="field"><label htmlFor="tambon">แขวง/ตำบล</label>
              <select id="tambon" value={filters.tambon} disabled={!filters.amphur} onChange={(event) => update("tambon", event.target.value)}>
                <option value="">-- เลือกตำบล --</option>{tambons.map((item) => <option key={item}>{item}</option>)}
              </select>
            </div>
            <AreaField label="ขนาดเนื้อที่ (ไร่)" condition={filters.raiCondition} value={filters.raiValue} onCondition={(value) => update("raiCondition", value)} onValue={(value) => update("raiValue", value)} />
            <AreaField label="ขนาดเนื้อที่ (งาน)" condition={filters.nganCondition} value={filters.nganValue} onCondition={(value) => update("nganCondition", value)} onValue={(value) => update("nganValue", value)} />
            <AreaField label="ขนาดเนื้อที่ (ตร.ว.)" condition={filters.squareWahCondition} value={filters.squareWahValue} onCondition={(value) => update("squareWahCondition", value)} onValue={(value) => update("squareWahValue", value)} />
            <button className="search-button" type="submit" disabled={loading}><Icon name="search" />{loading ? "กำลังค้นหา..." : "ค้นหาทรัพย์"}</button>
          </form>
        )}
      </section>
      <section className="results-section">
        <div className="results-heading"><div><span>ผลการค้นหา</span><h2>ทรัพย์ที่พบทั้งหมด</h2></div><strong>{assets.length} รายการ</strong></div>
        {error && <div className="error-state">{error}</div>}
        {!loading && !error && visibleAssets.length === 0 && <div className="empty-state">ไม่พบทรัพย์ตามเงื่อนไข ลองปรับพื้นที่ค้นหาอีกครั้ง</div>}
        <div className="asset-grid">{visibleAssets.map((asset) => <AssetCard key={asset.id} asset={asset} />)}</div>
        {assets.length > PAGE_SIZE && <div className="pagination">
          <button disabled={page === 1} onClick={() => setPage(page - 1)}>ก่อนหน้า</button><span>หน้า {page} / {totalPages}</span><button disabled={page === totalPages} onClick={() => setPage(page + 1)}>ถัดไป</button>
        </div>}
      </section>
    </main>
  );
}
