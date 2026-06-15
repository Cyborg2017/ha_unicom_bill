class HaUnicomCard extends HTMLElement {
  static getConfigElement() {
    return document.createElement("ha-unicom-card-editor");
  }

  static getStubConfig() {
    return {
      type: "custom:ha-unicom-card",
      title: "中国联通话费",
      balance_warning_below: 20,
      usage_warning_percent: 80,
      usage_danger_percent: 95,
      show_details: true,
    };
  }

  setConfig(config) {
    this.config = {
      title: "中国联通话费",
      balance_warning_below: 20,
      usage_warning_percent: 80,
      usage_danger_percent: 95,
      show_details: true,
      ...config,
    };
    if (this.config.device_id === "") delete this.config.device_id;
    this.entities = [];
    this.device = null;
    this.discoveryKey = "";
    this.render();
  }

  connectedCallback() {
    if (this._moreInfoHandler) return;
    this._moreInfoHandler = (event) => {
      // 手风琴折叠/展开
      const accordionHeader = event.target.closest(".accordion-header");
      if (accordionHeader && this.contains(accordionHeader)) {
        event.stopPropagation();
        const accordion = accordionHeader.closest(".accordion");
        if (accordion) accordion.classList.toggle("open");
        return;
      }
      // 实体详情弹窗
      const target = event.target.closest("[data-entity-id]");
      if (!target || !this.contains(target)) return;

      const entityId = target.dataset.entityId;
      if (!entityId) return;
      event.stopPropagation();
      this.dispatchEvent(new CustomEvent("hass-more-info", {
        detail: { entityId },
        bubbles: true,
        composed: true,
      }));
    };
    this.addEventListener("click", this._moreInfoHandler);
  }

  disconnectedCallback() {
    if (!this._moreInfoHandler) return;
    this.removeEventListener("click", this._moreInfoHandler);
    this._moreInfoHandler = null;
  }

  set hass(hass) {
    this._hass = hass;
    this.discoverEntities();
    this.render();
  }

  getCardSize() {
    return 5;
  }

  async discoverEntities() {
    if (!this._hass?.callWS || this.discovering) return;

    const key = JSON.stringify({
      device_id: this.config.device_id,
      states: Object.keys(this._hass.states || {}).length,
    });
    if (this.discoveryKey === key && this.entities.length) return;

    this.discovering = true;
    try {
      const [devices, registry] = await Promise.all([
        this._hass.callWS({ type: "config/device_registry/list" }),
        this._hass.callWS({ type: "config/entity_registry/list" }),
      ]);

      const unicomDevice = this.config.device_id
        ? devices.find((device) => device.id === this.config.device_id)
        : this.findUnicomDevice(devices, registry);
      const deviceId = unicomDevice?.id || this.config.device_id;

      this.device = unicomDevice || null;
      this.entities = registry
        .filter((entry) => entry.device_id === deviceId)
        .filter((entry) => !entry.disabled_by && !entry.hidden_by)
        .filter((entry) => this._hass.states[entry.entity_id])
        .sort((a, b) => this.sortRank(a).localeCompare(this.sortRank(b)));
      this.discoveryKey = key;
    } catch (error) {
      this.discoveryError = error;
    } finally {
      this.discovering = false;
      this.render(true);
    }
  }

  findUnicomDevice(devices, registry) {
    const text = (device) => [
      device.name_by_user,
      device.name,
      device.manufacturer,
      device.model,
    ].filter(Boolean).join(" ");

    const candidates = devices.filter((device) =>
      /Unicom|中国联通|联通|china[_ -]?unicom/i.test(text(device))
    );
    return candidates
      .map((device) => ({
        device,
        count: registry.filter((entry) => entry.device_id === device.id && entry.entity_id?.startsWith("sensor.")).length,
      }))
      .sort((a, b) => b.count - a.count)[0]?.device || null;
  }

  sortRank(entry) {
    const name = this.entryName(entry);
    const entityId = entry.entity_id;
    const rank = [
      [/账户余额|balance/, "01"],
      [/本月话费|real_fee/, "02"],
      [/上月结余话费|can_use_value/, "03"],
      [/账户欠费|total_owed/, "04"],
      [/流量使用比例|data_ratio/, "05"],
      [/语音使用比例|voice_ratio/, "06"],
      [/短信使用比例|sms_ratio/, "065"],
      [/已用流量\(合计\)|data_usage/, "07"],
      [/剩余流量\(合计\)|data_available/, "08"],
      [/流量总量\(合计\)|data_total/, "09"],
      [/超支流量|data_exceed/, "10"],
      [/上月转接流量|data_carried_over/, "11"],
      [/已用语音|voice_usage/, "12"],
      [/剩余语音|voice_available/, "13"],
      [/语音总量|voice_total/, "14"],
      [/已用短信|sms_usage/, "15"],
      [/剩余短信|sms_available/, "16"],
      [/短信总量|sms_total/, "17"],
      [/已用流量\(通用\)|data_usage_general/, "18"],
      [/剩余流量\(通用\)|data_available_general/, "19"],
      [/流量总量\(通用\)|data_total_general/, "20"],
      [/已用流量\(专属\)|data_usage_exclusive/, "21"],
      [/剩余流量\(专属\)|data_available_exclusive/, "22"],
      [/流量总量\(专属\)|data_total_exclusive/, "23"],
      [/已用流量\(其他\)|data_usage_other/, "24"],
      [/剩余流量\(其他\)|data_available_other/, "25"],
      [/流量总量\(其他\)|data_total_other/, "26"],
    ].find(([pattern]) => pattern.test(name) || pattern.test(entityId))?.[1] || "99";
    return `${rank}-${entityId}`;
  }

  entryName(entry) {
    return entry.name || entry.original_name || this._hass?.states?.[entry.entity_id]?.attributes?.friendly_name || entry.entity_id;
  }

  label(entry) {
    return this.entryName(entry)
      .replace(/^\d{3}[*\d_]+ ?/, "")
      .replace(/^联通/, "")
      .trim();
  }

  state(entityId) {
    return this._hass?.states?.[entityId];
  }

  findEntity(patterns) {
    return this.entities.find((entry) => {
      const text = `${entry.entity_id} ${this.entryName(entry)}`;
      return patterns.some((pattern) => pattern.test(text));
    });
  }

  value(entry) {
    const state = entry && this.state(entry.entity_id);
    if (!state) return "--";
    const unit = state.attributes?.unit_of_measurement || "";
    return `${state.state}${unit ? ` ${unit}` : ""}`;
  }

  stateValue(entry) {
    const state = entry && this.state(entry.entity_id);
    if (!state) return "--";
    return state.state;
  }

  numberValue(entry) {
    const state = entry && this.state(entry.entity_id);
    const value = Number.parseFloat(state?.state);
    return Number.isFinite(value) ? value : null;
  }

  render(force = false) {
    if (!this.config) return;
    const key = JSON.stringify({
      config: this.config,
      entities: this.entities.map((entry) => [entry.entity_id, this.state(entry.entity_id)?.state]),
      discovering: this.discovering,
      error: Boolean(this.discoveryError),
    });
    if (!force && this.lastRenderKey === key) return;
    this.lastRenderKey = key;

    const balance = this.findEntity([/账户余额|balance/]);
    const cost = this.findEntity([/本月话费|real_fee/]);
    const carryOver = this.findEntity([/上月结余话费|can_use_value/]);
    const owed = this.findEntity([/账户欠费|total_owed/]);
    const dataRate = this.findEntity([/流量使用比例|data_ratio/]);
    const voiceRate = this.findEntity([/语音使用比例|voice_ratio/]);
    const smsRate = this.findEntity([/短信使用比例|sms_ratio/]);
    const dataExceed = this.findEntity([/超支流量|data_exceed/]);

    this.innerHTML = `
      <ha-card>
        <div class="unicom-card">
          <div class="card-header">
            <div class="card-title">
              <img class="card-logo" src="/ha_unicom_bill-local/logo.png" alt="logo">
              ${this.escape(this.config.title || "中国联通话费")}
            </div>
          </div>
          ${this.discoveryError ? `<div class="message">实体读取失败：${this.escape(this.discoveryError.message || this.discoveryError)}</div>` : ""}
          ${this.discovering && !this.entities.length ? `<div class="message">正在读取设备实体...</div>` : ""}
          ${!this.discovering && !this.entities.length ? `<div class="message">未找到可显示实体，请在卡片编辑器选择联通设备。</div>` : ""}
          ${this.entities.length ? `
            <div class="summary-row">
              ${this.summaryItem("账户余额", balance, "mdi:wallet", "green")}
              ${this.summaryItem("本月话费", cost, "mdi:currency-cny", "orange")}
              ${this.summaryItem("上月结余", carryOver, "mdi:arrow-left-bold", "blue")}
              ${this.summaryItem("账户欠费", owed, "mdi:cash-minus", "red")}
            </div>
            <div class="meters">
              ${this.progress("流量", dataRate, this.findEntity([/剩余流量\(合计\)|data_available/]), this.findEntity([/流量总量\(合计\)|data_total/]))}
              ${this.progress("语音", voiceRate, this.findEntity([/剩余语音|voice_available/]), this.findEntity([/语音总量|voice_total/]))}
              ${this.progress("短信", smsRate, this.findEntity([/剩余短信|sms_available/]), this.findEntity([/短信总量|sms_total/]), "条")}
            </div>
            <div class="accordions">
              ${this.accordionSection("流量明细", "mdi:cellphone-link", [/流量.*通用|general/, /流量.*专属|exclusive/, /流量.*其他|other/, /流量总量\(合计\)|data_total/, /剩余流量\(合计\)|data_available/, /已用流量\(合计\)|data_usage/])}
              ${this.accordionSection("语音明细", "mdi:phone", [/已用语音|voice_usage/, /语音总量|voice_total/, /剩余语音|voice_available/], {"/语音/": "min"})}
              ${this.accordionSection("短信明细", "mdi:message-text", [/已用短信|sms_usage/, /短信总量|sms_total/, /剩余短信|sms_available/], {"/短信/": "条"})}
            </div>
          ` : ""}
        </div>
        <style>
          .unicom-card {
            padding: 0;
            color: var(--primary-text-color);
          }
          .card-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 16px 20px 12px;
            border-bottom: 2px solid transparent;
            border-image: linear-gradient(90deg, #e65100, #ff8a50, #ffab91, transparent) 1;
          }
          .card-title {
            font-size: 18px;
            font-weight: bold;
            color: var(--primary-text-color);
            display: flex;
            align-items: center;
            gap: 10px;
          }
          .card-title img.card-logo {
            width: 30px;
            height: 30px;
            border-radius: 6px;
            object-fit: contain;
            box-shadow: 0 1px 4px rgba(0,0,0,0.12);
          }
          .message {
            color: var(--secondary-text-color);
            padding: 12px 16px 4px;
            font-size: 14px;
          }

          /* 汇总行 - 参考 hfwater 风格 */
          .summary-row {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            padding: 12px 12px;
            gap: 8px;
          }
          .summary-item {
            text-align: center;
            background: var(--secondary-background-color, rgba(0,0,0,0.03));
            border-radius: 10px;
            padding: 10px 4px 8px;
            transition: transform 0.15s, box-shadow 0.15s;
            cursor: pointer;
          }
          .summary-item:hover {
            transform: translateY(-2px);
            box-shadow: 0 3px 10px rgba(0,0,0,0.08);
          }
          .summary-icon {
            margin-bottom: 4px;
          }
          .summary-icon ha-icon {
            --mdi-icon-size: 20px;
            color: var(--secondary-text-color, #999);
          }
          .summary-value {
            font-size: 18px;
            font-weight: bold;
            line-height: 1.3;
          }
          .summary-value.green { color: #43A047; }
          .summary-value.orange { color: #FF6D00; }
          .summary-value.blue { color: #1E88E5; }
          .summary-value.red { color: #EF5350; }
          .summary-label {
            font-size: 10px;
            color: var(--secondary-text-color, #999);
            margin-top: 2px;
            letter-spacing: 0.3px;
            line-height: 1.3;
            word-break: keep-all;
          }

          /* 进度条区域 - 参考 hfwater tier 风格 */
          .meters {
            display: grid;
            gap: 10px;
            margin-bottom: 12px;
            padding: 0 12px;
          }
          .meter {
            background: var(--secondary-background-color, rgba(0,0,0,0.03));
            border-radius: 10px;
            padding: 12px 14px;
          }
          .meter-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
          }
          .meter-name {
            font-size: 14px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 6px;
            color: var(--primary-text-color);
          }
          .meter-dot {
            width: 14px;
            height: 14px;
            border-radius: 50%;
            flex-shrink: 0;
          }
          .meter-dot.normal { background: linear-gradient(135deg, #66BB6A, #43A047); }
          .meter-dot.warn { background: linear-gradient(135deg, #FFB74D, #f57c00); }
          .meter-dot.danger { background: linear-gradient(135deg, #EF5350, #dd2c00); }
          .meter-volume {
            font-size: 14px;
            font-weight: 600;
            color: var(--primary-text-color);
          }
          .meter-bar {
            height: 8px;
            background: #E0E0E0;
            border-radius: 4px;
            overflow: hidden;
            margin-bottom: 6px;
          }
          .meter-bar-fill {
            height: 100%;
            border-radius: 4px;
            transition: width 0.3s ease;
          }
          .meter-bar-fill.normal { background: linear-gradient(90deg, #66BB6A, #43A047); }
          .meter-bar-fill.warn { background: linear-gradient(90deg, #FFB74D, #f57c00); }
          .meter-bar-fill.danger { background: linear-gradient(90deg, #EF5350, #dd2c00); }
          .meter-info {
            display: flex;
            justify-content: space-between;
            font-size: 11px;
            color: var(--secondary-text-color, #999);
          }
          .accordions {
            display: grid;
            gap: 8px;
            padding: 0 12px 12px;
          }
          .accordion {
            border-radius: 10px;
            overflow: hidden;
            border: none;
            background: transparent;
          }
          .accordion-header {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 10px 12px;
            cursor: pointer;
            user-select: none;
            transition: background 0.15s ease;
          }
          .accordion-header:hover {
            background: rgba(230, 81, 0, 0.06);
          }
          .accordion-icon {
            --mdc-icon-size: 22px;
            color: #e65100;
          }
          .accordion-title {
            flex: 1;
            font-size: 13px;
            font-weight: 600;
            color: var(--primary-text-color);
          }
          .accordion-chevron {
            --mdc-icon-size: 22px;
            color: var(--secondary-text-color);
            transition: transform 0.25s ease;
          }
          .accordion.open .accordion-chevron {
            transform: rotate(180deg);
          }
          .accordion-body {
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.3s ease;
          }
          .accordion.open .accordion-body {
            max-height: 600px;
          }
          .entity-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 8px;
            padding: 0 12px 10px;
          }
          .entity-row {
            background: rgba(255, 138, 80, 0.12);
            border: none;
            border-radius: 10px;
            padding: 10px 12px;
            min-width: 0;
            cursor: pointer;
            transition: background 0.15s ease, transform 0.15s ease;
          }
          .entity-row:hover {
            background: rgba(230, 81, 0, 0.20);
            transform: translateY(-1px);
          }
          .row-name {
            color: var(--secondary-text-color);
            font-size: 12px;
          }
          .row-value {
            font-weight: 600;
            margin-top: 4px;
            overflow-wrap: anywhere;
          }
          @media (max-width: 480px) {
            .card-header { padding: 14px 16px 10px; }
            .summary-row { padding: 10px 8px; gap: 6px; }
            .summary-item { padding: 8px 2px 6px; }
            .summary-value { font-size: 16px; }
            .summary-label { font-size: 9px; }
            .entity-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 6px; }
            .entity-row { padding: 8px; }
            .row-value { font-size: 13px; }
            .meter-detail { font-size: 12px; }
          }
          @media (max-width: 360px) {
            .summary-row, .entity-grid { gap: 5px; }
            .summary-item, .entity-row { padding: 7px; }
          }
        </style>
      </ha-card>
    `;
  }

  metric(label, entry, icon, warning = false) {
    return `
      <div class="metric${warning ? " warning" : ""}"${this.entityAttr(entry)}>
        <ha-icon icon="${icon}"></ha-icon>
        <div class="metric-label">${this.escape(label)}</div>
        <div class="metric-value">${this.escape(this.value(entry))}</div>
      </div>
    `;
  }

  summaryItem(label, entry, icon, color) {
    return `
      <div class="summary-item"${this.entityAttr(entry)}>
        <div class="summary-icon"><ha-icon icon="${icon}"></ha-icon></div>
        <div class="summary-value ${color || ""}">${this.escape(this.stateValue(entry))}</div>
        <div class="summary-label">${this.escape(label)}</div>
      </div>
    `;
  }

  smallMetric(label, entry, icon, warning = false) {
    return `
      <div class="small-metric${warning ? " warning" : ""}"${this.entityAttr(entry)}>
        <ha-icon icon="${icon}"></ha-icon>
        <span>${this.escape(label)}:</span>
        <strong>${this.escape(this.value(entry))}</strong>
      </div>
    `;
  }

  progress(label, rateEntry, remainEntry, totalEntry, unit = "") {
    const rate = this.numberValue(rateEntry);
    const percent = rate === null ? 0 : Math.max(0, Math.min(100, rate));
    const level = this.usageLevel(rate);
    const dotClass = level === "danger" ? "danger" : level === "warn" ? "warn" : "normal";
    const fillClass = level === "danger" ? "danger" : level === "warn" ? "warn" : "normal";
    return `
      <div class="meter">
        <div class="meter-header">
          <span class="meter-name"><span class="meter-dot ${dotClass}"></span>${this.escape(label)}</span>
          <span class="meter-volume">${this.clickableValue(rateEntry)}</span>
        </div>
        <div class="meter-bar"><div class="meter-bar-fill ${fillClass}" style="width:${percent}%"></div></div>
        <div class="meter-info">
          <span>剩余 ${this.clickableValue(remainEntry)}${unit ? ` ${this.escape(unit)}` : ""}</span>
          <span>总量 ${this.clickableValue(totalEntry)}${unit ? ` ${this.escape(unit)}` : ""}</span>
        </div>
      </div>
    `;
  }

  clickableValue(entry, extraClass = "") {
    const className = `clickable-value${extraClass ? ` ${extraClass}` : ""}`;
    return `<span class="${className}"${this.entityAttr(entry)}>${this.escape(this.value(entry))}</span>`;
  }

  isBalanceLow(entry) {
    const threshold = Number.parseFloat(this.config.balance_warning_below);
    const value = this.numberValue(entry);
    return Number.isFinite(threshold) && threshold > 0 && value !== null && value < threshold;
  }

  isOwedHigh(entry) {
    const value = this.numberValue(entry);
    return value !== null && value > 0;
  }

  usageLevel(value) {
    if (value === null) return "";
    const warning = Number.parseFloat(this.config.usage_warning_percent);
    const danger = Number.parseFloat(this.config.usage_danger_percent);
    if (Number.isFinite(danger) && danger > 0 && value >= danger) return "danger";
    if (
      Number.isFinite(warning)
      && warning > 0
      && value >= warning
      && (!Number.isFinite(danger) || danger <= 0 || warning < danger)
    ) return "warn";
    return "";
  }

  accordionSection(title, icon, patterns, unitMap = {}) {
    const rows = this.entities.filter((entry) => {
      const text = `${entry.entity_id} ${this.entryName(entry)}`;
      return patterns.some((pattern) => pattern.test(text));
    });
    // 二次排序：同子分类横排（每行 已用→剩余→总量）
    rows.sort((a, b) => {
      const nameA = this.entryName(a);
      const nameB = this.entryName(b);
      const idA = a.entity_id;
      const idB = b.entity_id;
      const groupRank = (name, id) => {
        const t = `${id} ${name}`;
        if (/通用|general/.test(t)) return "1";
        if (/专属|exclusive/.test(t)) return "2";
        if (/其他|other/.test(t)) return "3";
        return "0";
      };
      const typeRank = (name, id) => {
        if (/已用|usage/.test(name) || /usage/.test(id)) return "1";
        if (/剩余|available/.test(name) || /available/.test(id)) return "2";
        if (/总量|total/.test(name) || /total/.test(id)) return "3";
        return "9";
      };
      const ga = groupRank(nameA, idA), gb = groupRank(nameB, idB);
      if (ga !== gb) return ga.localeCompare(gb);
      return typeRank(nameA, idA).localeCompare(typeRank(nameB, idB));
    });
    if (!rows.length) return "";
    const sectionId = `accordion-${title}`;
    const isOpen = this.config?.show_details !== false;
    return `
      <div class="accordion${isOpen ? " open" : ""}" data-accordion="${sectionId}">
        <div class="accordion-header" @click="${sectionId}">
          <ha-icon class="accordion-icon" icon="${icon}"></ha-icon>
          <span class="accordion-title">${this.escape(title)}</span>
          <ha-icon class="accordion-chevron" icon="mdi:chevron-down"></ha-icon>
        </div>
        <div class="accordion-body" id="${sectionId}">
          <div class="entity-grid">
            ${rows.map((entry) => {
              const text = `${entry.entity_id} ${this.entryName(entry)}`;
              const overrideUnit = Object.keys(unitMap).find(p => new RegExp(p).test(text));
              const displayValue = overrideUnit
                ? `${this.stateValue(entry)} ${unitMap[overrideUnit]}`
                : this.value(entry);
              return `
              <div class="entity-row"${this.entityAttr(entry)}>
                <div class="row-name">${this.escape(this.label(entry))}</div>
                <div class="row-value">${this.escape(displayValue)}</div>
              </div>
            `}).join("")}
          </div>
        </div>
      </div>
    `;
  }

  escape(value) {
    return String(value ?? "").replace(/[&<>"']/g, (char) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#039;",
    }[char]));
  }

  entityAttr(entry) {
    return entry?.entity_id ? ` data-entity-id="${this.escape(entry.entity_id)}"` : "";
  }
}

class HaUnicomCardEditor extends HTMLElement {
  setConfig(config) {
    this.config = {
      title: "中国联通话费",
      balance_warning_below: 20,
      usage_warning_percent: 80,
      usage_danger_percent: 95,
      show_details: true,
      ...config,
    };
    if (this.config.device_id === "") delete this.config.device_id;
    this.render();
  }

  set hass(hass) {
    this._hass = hass;
    if (this._form) {
      this._form.hass = hass;
      return;
    }
    this.render();
  }

  render() {
    if (!this._hass || !this.config) return;
    if (!this._form) {
      this.innerHTML = `<ha-form></ha-form>`;
      this._form = this.querySelector("ha-form");
      this._form.schema = [
        { name: "title", selector: { text: {} } },
        { name: "device_id", selector: { device: {} } },
        { name: "balance_warning_below", selector: { number: { min: 0, mode: "box", unit_of_measurement: "元" } } },
        { name: "usage_warning_percent", selector: { number: { min: 0, max: 100, mode: "box", unit_of_measurement: "%" } } },
        { name: "usage_danger_percent", selector: { number: { min: 0, max: 100, mode: "box", unit_of_measurement: "%" } } },
        { name: "show_details", selector: { boolean: {} } },
      ];
      this._form.computeLabel = (schema) => ({
        title: "标题",
        device_id: "联通设备",
        balance_warning_below: "余额低于此值标红",
        usage_warning_percent: "使用率提醒百分比",
        usage_danger_percent: "使用率危险百分比",
        show_details: "明细展开显示",
      }[schema.name] || schema.name);
      this._form.addEventListener("value-changed", (event) => {
        event.stopPropagation();
        const nextConfig = { ...this.config, ...event.detail.value };
        if (JSON.stringify(nextConfig) === JSON.stringify(this.config)) return;
        this.config = nextConfig;
        this.dispatchEvent(new CustomEvent("config-changed", {
          detail: { config: this.config },
          bubbles: true,
          composed: true,
        }));
      });
    }
    this._form.hass = this._hass;
    this._form.data = this.config;
  }
}

customElements.define("ha-unicom-card", HaUnicomCard);
customElements.define("ha-unicom-card-editor", HaUnicomCardEditor);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "ha-unicom-card",
  name: "HA 联通卡片",
  description: "选择中国联通设备后自动读取并展示余额、话费、流量和通话实体。",
});
