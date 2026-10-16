/**
 * PharmPulse Pro - Business Intelligence & Financial Analytics Controller
 * Renders executive KPI metrics and dynamic interactive SVG charts
 * for 14-day sales trends, category distribution, and expiry risk valuation.
 */

class AnalyticsEngine {
  constructor() {
    this.kpis = null;
    this.chartData = null;
    this.init();
  }

  init() {}

  async loadDashboardKPIs() {
    try {
      const [kpiRes, chartRes] = await Promise.all([
        window.pharmApp.fetchWithAuth('/api/analytics/kpis'),
        window.pharmApp.fetchWithAuth('/api/analytics/charts')
      ]);

      const kpiData = await kpiRes.json();
      const chartData = await chartRes.json();

      if (kpiData.success) {
        this.kpis = kpiData;
        this.renderKPIs();
      }

      if (chartData.success) {
        this.chartData = chartData;
        this.renderTrendChart(chartData.daily_trends);
        this.renderExpiryRiskRadar(chartData.risk_matrix);
        this.renderTopSellingTable(chartData.top_selling);
      }
    } catch (e) {
      console.error("Error loading dashboard metrics:", e);
    }
  }

  renderKPIs() {
    if (!this.kpis) return;
    const revEl = document.getElementById('kpi-today-rev');
    const growthEl = document.getElementById('kpi-growth-pct');
    const profitEl = document.getElementById('kpi-all-profit');
    const marginEl = document.getElementById('kpi-profit-margin');
    const lowStockEl = document.getElementById('kpi-low-stock');
    const expiringEl = document.getElementById('kpi-expiring');

    if (revEl) revEl.textContent = `ZK ${this.kpis.today_revenue.toFixed(2)}`;
    if (growthEl) {
      growthEl.textContent = `${this.kpis.revenue_growth_pct >= 0 ? '+' : ''}${this.kpis.revenue_growth_pct}%`;
      growthEl.style.color = this.kpis.revenue_growth_pct >= 0 ? 'var(--primary)' : 'var(--danger)';
    }
    if (profitEl) profitEl.textContent = `ZK ${this.kpis.all_time_profit.toFixed(2)}`;
    if (marginEl) marginEl.textContent = `${this.kpis.profit_margin_pct}%`;
    if (lowStockEl) lowStockEl.textContent = this.kpis.low_stock_count;
    if (expiringEl) expiringEl.textContent = this.kpis.expiring_count;

    // Update sidebar badges
    const lowBadge = document.getElementById('sidebar-low-stock-badge');
    const rxBadge = document.getElementById('sidebar-pending-rx-badge');
    if (lowBadge) {
      lowBadge.textContent = this.kpis.low_stock_count;
      lowBadge.style.display = this.kpis.low_stock_count > 0 ? 'inline-block' : 'none';
    }
    if (rxBadge) {
      rxBadge.textContent = this.kpis.pending_rx_count;
      rxBadge.style.display = this.kpis.pending_rx_count > 0 ? 'inline-block' : 'none';
    }
  }

  // ==========================================
  // SVG AREA / LINE CHART (14-Day Trajectory)
  // ==========================================
  renderTrendChart(trends) {
    const container = document.getElementById('dashboard-trend-chart');
    if (!container || !trends || trends.length === 0) return;

    const width = 600;
    const height = 240;
    const padding = { top: 20, right: 30, bottom: 40, left: 60 };

    const maxVal = Math.max(...trends.map(t => Math.max(t.revenue, t.profit, 100))) * 1.15;
    const chartW = width - padding.left - padding.right;
    const chartH = height - padding.top - padding.bottom;

    const pointsRev = trends.map((t, idx) => {
      const x = padding.left + (idx / (trends.length - 1)) * chartW;
      const y = padding.top + chartH - (t.revenue / maxVal) * chartH;
      return { x, y, val: t.revenue, date: t.sale_date };
    });

    const pointsProf = trends.map((t, idx) => {
      const x = padding.left + (idx / (trends.length - 1)) * chartW;
      const y = padding.top + chartH - (t.profit / maxVal) * chartH;
      return { x, y, val: t.profit, date: t.sale_date };
    });

    const pathRev = pointsRev.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ');
    const pathArea = `${pathRev} L ${pointsRev[pointsRev.length - 1].x.toFixed(1)} ${(padding.top + chartH).toFixed(1)} L ${pointsRev[0].x.toFixed(1)} ${(padding.top + chartH).toFixed(1)} Z`;

    const pathProf = pointsProf.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ');

    // Horizontal Grid Lines
    const gridLines = [0, 0.25, 0.5, 0.75, 1.0].map(ratio => {
      const y = padding.top + chartH * (1 - ratio);
      const val = (maxVal * ratio).toFixed(0);
      return `
        <line x1="${padding.left}" y1="${y}" x2="${width - padding.right}" y2="${y}" stroke="var(--border-subtle)" stroke-dasharray="4 4" />
        <text x="${padding.left - 10}" y="${y + 4}" fill="var(--text-subtle)" font-size="10" text-anchor="end" font-family="var(--font-mono)">ZK ${val}</text>
      `;
    }).join('');

    // X Axis Labels (every 3 days)
    const xLabels = pointsRev.filter((_, i) => i % 3 === 0 || i === pointsRev.length - 1).map(p => {
      const d = p.date.substring(5); // MM-DD
      return `<text x="${p.x}" y="${height - 10}" fill="var(--text-subtle)" font-size="10" text-anchor="middle" font-family="var(--font-mono)">${d}</text>`;
    }).join('');

    const circlesRev = pointsRev.map(p => `
      <circle cx="${p.x}" cy="${p.y}" r="4" fill="#10b981" stroke="var(--bg-surface)" stroke-width="2">
        <title>${p.date}: ZK ${p.val.toFixed(2)} Revenue</title>
      </circle>
    `).join('');

    const circlesProf = pointsProf.map(p => `
      <circle cx="${p.x}" cy="${p.y}" r="3.5" fill="#6366f1" stroke="var(--bg-surface)" stroke-width="1.5">
        <title>${p.date}: ZK ${p.val.toFixed(2)} Profit</title>
      </circle>
    `).join('');

    container.innerHTML = `
      <svg viewBox="0 0 ${width} ${height}" style="width:100%; height:100%; overflow:visible;">
        <defs>
          <linearGradient id="revGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#10b981" stop-opacity="0.25"/>
            <stop offset="100%" stop-color="#10b981" stop-opacity="0.0"/>
          </linearGradient>
        </defs>

        ${gridLines}
        ${xLabels}

        <!-- Revenue Area & Line -->
        <path d="${pathArea}" fill="url(#revGrad)" />
        <path d="${pathRev}" fill="none" stroke="#10b981" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
        ${circlesRev}

        <!-- Profit Line -->
        <path d="${pathProf}" fill="none" stroke="#6366f1" stroke-width="2" stroke-dasharray="3 3" stroke-linecap="round"/>
        ${circlesProf}

        <!-- Legend -->
        <g transform="translate(${width - 200}, 15)">
          <line x1="0" y1="0" x2="18" y2="0" stroke="#10b981" stroke-width="3" />
          <text x="24" y="4" fill="var(--text-muted)" font-size="11" font-weight="700">Revenue</text>
          <line x1="90" y1="0" x2="108" y2="0" stroke="#6366f1" stroke-width="2" stroke-dasharray="3 3"/>
          <text x="114" y="4" fill="var(--text-muted)" font-size="11" font-weight="700">Gross Margin</text>
        </g>
      </svg>
    `;
  }

  // ==========================================
  // EXPIRY RISK FINANCIAL RADAR
  // ==========================================
  renderExpiryRiskRadar(risk) {
    const container = document.getElementById('dashboard-expiry-matrix');
    if (!container || !risk) return;

    const val30 = risk.value_30d || 0;
    const val90 = risk.value_90d || 0;
    const valHealthy = risk.healthy_value || 1;
    const total = val30 + val90 + valHealthy;

    const pct30 = ((val30 / total) * 100).toFixed(1);
    const pct90 = ((val90 / total) * 100).toFixed(1);

    container.innerHTML = `
      <div>
        <div style="display:flex; justify-content:space-between; font-size:0.8rem; margin-bottom:4px;">
          <span style="color:var(--danger); font-weight:700;">Critical (< 30 Days):</span>
          <span style="font-family:var(--font-mono); font-weight:700;">ZK ${val30.toFixed(2)} (${pct30}%)</span>
        </div>
        <div style="width:100%; height:8px; background:var(--bg-surface); border-radius:4px; overflow:hidden;">
          <div style="width:${Math.max(4, pct30)}%; height:100%; background:var(--danger); border-radius:4px;"></div>
        </div>
      </div>

      <div>
        <div style="display:flex; justify-content:space-between; font-size:0.8rem; margin-bottom:4px;">
          <span style="color:var(--warning); font-weight:700;">Approaching (31 - 90 Days):</span>
          <span style="font-family:var(--font-mono); font-weight:700;">ZK ${val90.toFixed(2)} (${pct90}%)</span>
        </div>
        <div style="width:100%; height:8px; background:var(--bg-surface); border-radius:4px; overflow:hidden;">
          <div style="width:${Math.max(4, pct90)}%; height:100%; background:var(--warning); border-radius:4px;"></div>
        </div>
      </div>

      <div>
        <div style="display:flex; justify-content:space-between; font-size:0.8rem; margin-bottom:4px;">
          <span style="color:var(--primary); font-weight:700;">Healthy Shelf Life (> 90 Days):</span>
          <span style="font-family:var(--font-mono); font-weight:700;">ZK ${valHealthy.toFixed(2)}</span>
        </div>
        <div style="width:100%; height:8px; background:var(--bg-surface); border-radius:4px; overflow:hidden;">
          <div style="width:100%; height:100%; background:var(--primary); border-radius:4px;"></div>
        </div>
      </div>
    `;
  }

  renderTopSellingTable(items) {
    const tbody = document.getElementById('dashboard-top-tbody');
    const analyticsTbody = document.getElementById('analytics-top-tbody');
    if (!items || items.length === 0) return;

    const html = items.map(it => `
      <tr>
        <td style="font-weight:700; color:var(--text-main);">${it.brand_name}</td>
        <td style="font-size:0.82rem; color:var(--text-muted);">${it.generic_name}</td>
        <td><span class="badge badge-info">${it.category}</span></td>
        <td style="font-family:var(--font-mono); font-weight:700;">${it.total_units_sold} units</td>
        <td style="font-family:var(--font-mono); font-weight:700;">ZK ${it.total_revenue.toFixed(2)}</td>
        <td style="font-family:var(--font-mono); font-weight:700; color:var(--primary);">ZK ${it.total_profit.toFixed(2)}</td>
      </tr>
    `).join('');

    if (tbody) tbody.innerHTML = html;
    if (analyticsTbody) analyticsTbody.innerHTML = html;
  }

  // ==========================================
  // FULL BI VIEW CHARTS (Category & Payments)
  // ==========================================
  async loadCharts() {
    try {
      const res = await window.pharmApp.fetchWithAuth('/api/analytics/charts');
      const data = await res.json();
      if (data.success) {
        this.renderCategoryChart(data.category_split);
        this.renderPaymentChart(data.payment_methods);
        this.renderTopSellingTable(data.top_selling);
      }
    } catch (e) {
      console.error(e);
    }
  }

  renderCategoryChart(cats) {
    const container = document.getElementById('analytics-category-chart');
    if (!container || !cats || cats.length === 0) return;

    const maxRev = Math.max(...cats.map(c => c.revenue));

    container.innerHTML = `
      <div style="display:flex; flex-direction:column; gap:0.75rem; padding-top:0.5rem;">
        ${cats.map(c => {
          const pct = ((c.revenue / maxRev) * 100).toFixed(0);
          return `
            <div>
              <div style="display:flex; justify-content:space-between; font-size:0.82rem; margin-bottom:3px;">
                <span style="font-weight:700;">${c.category}</span>
                <span style="font-family:var(--font-mono); font-weight:700; color:var(--primary);">ZK ${c.revenue.toFixed(2)}</span>
              </div>
              <div style="width:100%; height:10px; background:var(--bg-surface); border-radius:5px; overflow:hidden;">
                <div style="width:${pct}%; height:100%; background:linear-gradient(90deg, var(--accent-cyan), var(--primary)); border-radius:5px;"></div>
              </div>
            </div>
          `;
        }).join('')}
      </div>
    `;
  }

  renderPaymentChart(methods) {
    const container = document.getElementById('analytics-payment-chart');
    if (!container || !methods || methods.length === 0) return;

    const totalAmt = methods.reduce((sum, m) => sum + m.total_amount, 0);

    container.innerHTML = `
      <div style="display:flex; flex-direction:column; gap:0.75rem; padding-top:0.5rem;">
        ${methods.map(m => {
          const pct = ((m.total_amount / totalAmt) * 100).toFixed(1);
          return `
            <div>
              <div style="display:flex; justify-content:space-between; font-size:0.82rem; margin-bottom:3px;">
                <span style="font-weight:700;">${m.payment_method} (${m.count} txns)</span>
                <span style="font-family:var(--font-mono); font-weight:700;">ZK ${m.total_amount.toFixed(2)} (${pct}%)</span>
              </div>
              <div style="width:100%; height:10px; background:var(--bg-surface); border-radius:5px; overflow:hidden;">
                <div style="width:${pct}%; height:100%; background:linear-gradient(90deg, var(--accent-indigo), #a855f7); border-radius:5px;"></div>
              </div>
            </div>
          `;
        }).join('')}
      </div>
    `;
  }
}

// Global instance
window.analyticsEngine = new AnalyticsEngine();
