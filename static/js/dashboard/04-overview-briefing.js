/* CTO Lens dashboard module: 04-overview-briefing.js */
// ===== Overview executive panels (Attention → Health → Briefing → Details) =====
function renderOverviewCollapsible(key, title, subtitle, bodyHtml, expanded, headerActionsHtml) {
    const bodyId = 'overview-' + key + '-body';
    const icon = expanded ? '\uD83D\uDD3D' : '\u25B6\uFE0F';
    const hiddenClass = expanded ? '' : ' hidden';
    let html = '<div class="bg-white rounded-lg shadow mb-4 overflow-hidden">';
    html += '<div class="cursor-pointer p-4 flex items-center justify-between hover:bg-gray-50 border-b border-gray-100" onclick="toggleSection(\'' + bodyId + '\')">';
    html += '<div class="min-w-0 flex-1"><h3 class="text-lg font-bold text-gray-800">' + title + '</h3>';
    if (subtitle) {
        html += '<p class="text-sm text-gray-500 mt-0.5 truncate' +
            (key === 'briefing' ? '" id="overview-briefing-subtitle"' : '"') + '>' + subtitle + '</p>';
    }
    html += '</div>';
    html += '<div class="flex items-center gap-2 shrink-0 ml-3" onclick="event.stopPropagation()">';
    if (headerActionsHtml) {
        html += headerActionsHtml;
    }
    html += '<span id="' + bodyId + '-icon" class="text-gray-500 cursor-pointer" onclick="toggleSection(\'' + bodyId + '\')">' + icon + '</span>';
    html += '</div></div>';
    html += '<div id="' + bodyId + '" class="p-4' + hiddenClass + '">' + bodyHtml + '</div></div>';
    return html;
}

function collectAttentionItems(portfolioData, briefingData, ctolensMode) {
    const briefing = briefingData && briefingData.briefing;

    if (ctolensMode && briefing && Array.isArray(briefing.signals)) {
        return briefing.signals
            .filter(function(s) {
                return s.severity === 'critical' || s.severity === 'warning';
            })
            .slice(0, 12)
            .map(function(s) {
                return {
                    severity: s.severity,
                    message: (s.project_name ? s.project_name + ': ' : '') + (s.description || s.title || s.signal_type)
                };
            });
    }

    // Prefer live portfolio attention (updates when assignments/budgets change).
    const ac = portfolioData && portfolioData.attention_center;
    if (ac && Array.isArray(ac.items)) {
        return ac.items.map(function(it) {
            return { severity: it.severity, message: it.message };
        });
    }

    // Fallback when portfolio dashboard is off but attention briefing exists.
    if (briefing && briefing.founder_attention_items && briefing.founder_attention_items.length) {
        return briefing.founder_attention_items.map(function(it) {
            return { severity: it.severity, message: it.message };
        });
    }
    const items = [];
    if (ac && ac.items) {
        ac.items.forEach(function(it) {
            items.push({ severity: it.severity, message: it.message });
        });
    }
    const risks = briefing && briefing.risk_signals;
    if (items.length === 0 && risks && risks.length) {
        risks.slice(0, 8).forEach(function(r) {
            items.push({ severity: r.severity || 'warning', message: r.detail || r.title });
        });
    }
    return items;
}

function _renderScoreTrendRow(label, trend) {
    if (!trend || trend.current == null) return '';
    let html = '<div class="flex items-center justify-between py-1.5 border-b border-gray-100 text-sm">';
    html += '<span class="text-gray-600">' + label + '</span><span class="font-medium text-gray-800">';
    if (trend.previous != null) {
        const ch = trend.change;
        const chColor = ch > 0 ? 'text-green-600' : (ch < 0 ? 'text-red-600' : 'text-gray-500');
        const chText = ch != null
            ? ' <span class="' + chColor + ' text-xs">(' + (ch > 0 ? '+' : '') + ch + (ch === 0 ? ', no change' : '') + ')</span>'
            : '';
        html += trend.previous + ' \u2192 ' + trend.current + chText;
    } else {
        html += trend.current + ' <span class="text-xs text-gray-400">(first snapshot)</span>';
    }
    html += '</span></div>';
    return html;
}

function renderAttentionItemsBody(items) {
    if (!items.length) {
        return '<div class="text-sm text-green-700 bg-green-50 border border-green-200 rounded p-3">Nothing needs attention right now.</div>';
    }
    let html = '';
    items.forEach(function(it) {
        const c = _pfSeverityColor(it.severity);
        html += '<div class="flex items-start gap-2 border-l-4 border-' + c + '-400 bg-' + c + '-50 px-3 py-2 mb-2 rounded-r">';
        html += '<span class="text-xs font-semibold uppercase text-' + c + '-700 shrink-0">' + (it.severity || 'info') + '</span>';
        html += '<span class="text-sm text-gray-700">' + it.message + '</span></div>';
    });
    return html;
}

function _pfEscapeHtml(text) {
    if (text == null) return '';
    return String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

function buildHealthScoreTips(data) {
    const h = (data && data.health_score) || {};
    const comps = h.components || {};
    const bv = (data && data.budget_variance) || {};
    const ch = (data && data.connector_health) || {};
    const ac = (data && data.attention_center) || {};
    const summary = (data && data.summary) || {};
    const intro =
        'Overall score averages Financial, Connectors, and Delivery (each 0–100). ' +
        'Bands: 80+ healthy, 60–79 at risk, below 60 critical.';
    const componentTips = [];
    const drivers = [];

    function addComponent(label, score, okMsg, lowMsg) {
        const line = label + ' ' + score + '/100 — ' + (score >= 80 ? okMsg : lowMsg);
        componentTips.push(line);
        if (score != null && score < 80) {
            drivers.push(line);
        }
    }

    if (comps.financial == null) {
        componentTips.push('Financial — not included: no assignments have a target monthly burn set.');
    } else if (comps.financial >= 80) {
        addComponent(
            'Financial',
            comps.financial,
            'portfolio spend is on track vs targets.',
            'budget variance is lowering this component.'
        );
    } else {
        const pct = bv.portfolio_variance_pct;
        let lowMsg = 'budget variance is lowering this component.';
        if (pct != null && pct > 20) {
            lowMsg = 'portfolio is ' + pct + '% over total budget target (large overrun). Update targets or reduce burn.';
        } else if (pct != null && pct > 10) {
            lowMsg = 'portfolio is ' + pct + '% over total budget target. Review assignments over budget.';
        } else if (pct != null && pct > 5) {
            lowMsg = 'portfolio is slightly (' + pct + '%) over combined targets.';
        }
        addComponent('Financial', comps.financial, '', lowMsg);
    }

    if (comps.connector == null) {
        componentTips.push('Connectors — not included: no connectors are enabled on active assignments.');
    } else if (comps.connector >= 80) {
        addComponent(
            'Connectors',
            comps.connector,
            'enabled integrations have credentials configured.',
            'some enabled connectors still need credentials.'
        );
    } else {
        const ready = ch.readiness_pct;
        const missing = (ch.total_enabled || 0) - (ch.total_ready || 0);
        addComponent(
            'Connectors',
            comps.connector,
            '',
            'only ' + (ready != null ? ready : comps.connector) +
            '% of enabled connectors are fully configured' +
            (missing > 0 ? ' (' + missing + ' need credentials).' : '.')
        );
    }

    const active = summary.active_assignments || 0;
    const deliveryItems = (ac.items || []).filter(function(it) {
        return it.type === 'budget_overrun' || it.type === 'missing_target';
    });
    const deliveryFlagged = new Set();
    deliveryItems.forEach(function(it) {
        if (it.assignment_id) deliveryFlagged.add(it.assignment_id);
    });

    if (comps.delivery == null || active === 0) {
        componentTips.push('Delivery — not included: no active assignments.');
    } else if (comps.delivery >= 80) {
        addComponent(
            'Delivery',
            comps.delivery,
            'no budget or target gaps flagged on assignments.',
            'budget or target gaps are flagged on some assignments.'
        );
    } else {
        let lowMsg = deliveryFlagged.size + ' of ' + active +
            ' assignment(s) have budget or target gaps.';
        deliveryItems.slice(0, 3).forEach(function(it) {
            if (it.message) lowMsg += ' ' + it.message;
        });
        addComponent('Delivery', comps.delivery, '', lowMsg);
    }

    const scoreParts = [];
    if (comps.financial != null) scoreParts.push('Financial (' + comps.financial + ')');
    if (comps.connector != null) scoreParts.push('Connectors (' + comps.connector + ')');
    if (comps.delivery != null) scoreParts.push('Delivery (' + comps.delivery + ')');
    const formula = scoreParts.length
        ? 'Average of ' + scoreParts.join(', ') +
          (h.overall_score != null ? ' → ' + h.overall_score + '/100' : '')
        : '';

    return { intro: intro, components: componentTips, drivers: drivers, formula: formula };
}

function renderHealthScoreHelpIcon(data) {
    const tips = buildHealthScoreTips(data);
    const allLines = [tips.intro].concat(tips.components);
    const tipItems = allLines.map(function(t) {
        return '<li class="mb-1 leading-snug">' + _pfEscapeHtml(t) + '</li>';
    }).join('');
    return (
        '<span class="relative inline-flex align-middle group" onclick="event.stopPropagation()">' +
        '<button type="button" class="w-5 h-5 rounded-full bg-white/80 border border-current text-[10px] font-bold leading-none ' +
        'opacity-80 hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-blue-400" ' +
        'aria-label="How health score is calculated">?</button>' +
        '<span class="pointer-events-none absolute left-0 top-full mt-2 w-72 sm:w-96 p-3 bg-gray-900 text-white text-xs rounded-lg shadow-xl ' +
        'opacity-0 invisible group-hover:opacity-100 group-hover:visible group-focus-within:opacity-100 group-focus-within:visible z-50 transition-opacity">' +
        '<div class="font-semibold mb-2 text-sm">Why this score?</div>' +
        '<ul class="list-none space-y-1 max-h-64 overflow-y-auto">' + tipItems + '</ul></span></span>'
    );
}

function renderPortfolioHealthBody(data, briefing) {
    const s = data.summary || {};
    const h = data.health_score || {};
    const band = h.band || 'healthy';
    const bandColor = _pfBandColor(band);
    const trends = (data && data.score_trends) || (briefing && briefing.score_trends);
    const trendsSince = data && data.score_trends_since;
    let html = '<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-2">';
    html += '<div class="bg-' + bandColor + '-50 border border-' + bandColor + '-200 rounded-lg p-4 relative">';
    html += '<div class="text-sm font-medium text-' + bandColor + '-800 flex items-center gap-1">';
    html += 'Health Score' + renderHealthScoreHelpIcon(data) + '</div>';
    html += '<div class="text-3xl font-bold text-' + bandColor + '-600">' + (h.overall_score != null ? h.overall_score : '\u2014') + '<span class="text-base font-medium">/100</span></div>';
    html += '<div class="text-xs text-' + bandColor + '-700 mt-1 uppercase">' + band.replace('_', ' ') + '</div></div>';
    html += '<div class="bg-gray-50 border border-gray-200 rounded-lg p-4">';
    html += '<div class="text-sm font-medium text-gray-600">Active Assignments</div>';
    html += '<div class="text-3xl font-bold text-gray-800">' + (s.active_assignments || 0) + '</div>';
    html += '<div class="text-xs text-gray-500 mt-1">of ' + (s.total_assignments || 0) + ' total</div></div>';
    html += '<div class="bg-gray-50 border border-gray-200 rounded-lg p-4">';
    html += '<div class="text-sm font-medium text-gray-600">Monthly Burn</div>';
    html += '<div class="text-3xl font-bold text-gray-800">' + _pfMoney(s.total_monthly_burn) + '</div>';
    html += '<div class="text-xs text-gray-500 mt-1">target ' + _pfMoney(s.total_target_burn) + '</div></div>';
    html += '<div class="bg-gray-50 border border-gray-200 rounded-lg p-4">';
    html += '<div class="text-sm font-medium text-gray-600">Total Team</div>';
    html += '<div class="text-3xl font-bold text-gray-800">' + (s.total_team_size || 0) + '</div>';
    html += '<div class="text-xs text-gray-500 mt-1">across active</div></div></div>';
    if (h.components) {
        const comps = [];
        if (h.components.financial != null) comps.push('Financial ' + h.components.financial);
        if (h.components.connector != null) comps.push('Connectors ' + h.components.connector);
        if (h.components.delivery != null) comps.push('Delivery ' + h.components.delivery);
        if (comps.length) html += '<div class="text-xs text-gray-500">Breakdown: ' + comps.join(' \u00B7 ') + '</div>';
    }
    if (h.overall_score != null && h.overall_score < 80) {
        const tipData = buildHealthScoreTips(data);
        html += '<div class="mt-3 text-xs text-amber-900 bg-amber-50 border border-amber-200 rounded-lg p-3">';
        html += '<span class="font-semibold">Why it\u2019s below 80:</span>';
        if (tipData.formula) {
            html += '<p class="mt-1 text-amber-800">' + _pfEscapeHtml(tipData.formula) + '</p>';
        }
        if (tipData.drivers.length) {
            html += '<ul class="mt-1 list-disc ml-4 space-y-0.5">';
            tipData.drivers.forEach(function(t) {
                html += '<li>' + _pfEscapeHtml(t) + '</li>';
            });
            html += '</ul>';
        } else {
            html += '<p class="mt-1 text-amber-800">Component scores are mixed; see breakdown above.</p>';
        }
        html += '<span class="text-amber-700 block mt-1">Hover <strong>?</strong> on Health Score for full detail.</span></div>';
    }
    if (trends) {
        html += '<div class="mt-4 bg-gray-50 border border-gray-200 rounded-lg p-3">';
        html += '<div class="text-xs font-semibold text-gray-600 uppercase mb-1">Score Trends</div>';
        html += '<div class="text-xs text-gray-400 mb-2">Live scores vs last saved snapshot';
        if (trendsSince) {
            try {
                html += ' (' + new Date(trendsSince).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }) + ')';
            } catch (e) { /* ignore */ }
        }
        html += '. Refresh briefing after changes to update the baseline.</div>';
        html += _renderScoreTrendRow('Health Score', trends.health);
        html += _renderScoreTrendRow('Financial Score', trends.financial);
        html += _renderScoreTrendRow('Connector Score', trends.connector);
        html += _renderScoreTrendRow('Delivery Score', trends.delivery);
        html += '</div>';
    }
    return html;
}

function renderBriefingStaleBanner(staleness) {
    if (!staleness || !staleness.is_stale) return '';
    let html = '<div class="mb-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 bg-amber-50 border border-amber-200 rounded-lg p-3">';
    html += '<div class="text-sm text-amber-900"><span class="font-semibold">Briefing may be outdated.</span> ';
    html += _pfEscapeHtml(staleness.reason || 'Portfolio data has changed since this briefing was generated.');
    html += '</div>';
    html += '<div class="flex flex-wrap gap-2 shrink-0">';
    html += '<button type="button" onclick="refreshAttentionBriefing()" class="text-xs bg-amber-600 text-white px-3 py-1.5 rounded-lg hover:bg-amber-700">Update briefing (fast)</button>';
    html += '<button type="button" onclick="refreshAttentionBriefing(true)" class="text-xs text-indigo-700 hover:underline" title="Include live connector metrics (90+ seconds)">Refresh live metrics</button>';
    html += '</div></div>';
    return html;
}

function formatCtolenRunHeader(briefingData, briefing, ctolensOn, staleness) {
    if (ctolensOn && briefingData && briefingData.header_summary) {
        let line = briefingData.header_summary;
        if (staleness && staleness.metrics_stale) {
            line += ' · live metrics may be stale';
        }
        if (briefingData.schedule && briefingData.schedule.enabled) {
            line += ' · scheduled enrichment on';
        }
        return line;
    }
    return formatBriefingSubtitle(briefing, ctolensOn, staleness);
}

function renderCtolenDiagnosticsPanel(diagnostics) {
    if (!diagnostics) return '';
    const runs = diagnostics.connector_runs || [];
    const log = diagnostics.run_log || [];
    let html = '<details class="mt-4 border border-gray-200 rounded-lg bg-gray-50">';
    html += '<summary class="cursor-pointer px-4 py-3 text-sm font-semibold text-gray-800">Signal &amp; connector details</summary>';
    html += '<div class="px-4 pb-4 text-xs text-gray-700 space-y-3">';
    html += '<div>Run <span class="font-mono">' + _pfEscapeHtml(diagnostics.run_id || '—') + '</span>';
    html += ' · evaluated ' + (diagnostics.signals_evaluated_count || 0) + ' signals · shown ' + (diagnostics.signals_shown_count || 0) + '</div>';
    if (runs.length) {
        html += '<ul class="space-y-1">';
        runs.forEach(function(r) {
            html += '<li>' + _pfEscapeHtml(r.assignment_name || r.assignment_id) + ' · ' + _pfEscapeHtml(r.connector) + ' · ' + _pfEscapeHtml(r.status) + '</li>';
        });
        html += '</ul>';
    } else {
        html += '<div class="text-gray-500">No connector runs on last fast briefing.</div>';
    }
    if (log.length) {
        html += '<div class="font-semibold text-gray-800 mt-2">Recent runs</div><ul class="space-y-1">';
        log.slice(0, 5).forEach(function(entry) {
            html += '<li>' + _pfEscapeHtml(entry.run_type || '') + ' · ' + _pfEscapeHtml(entry.status || '') + ' · ' + _pfEscapeHtml(String(entry.duration_seconds || '')) + 's</li>';
        });
        html += '</ul>';
    }
    html += '</div></details>';
    return html;
}

function formatBriefingSubtitle(briefing, ctolensOn, staleness) {
    let subtitle = 'Executive narrative and signals';
    if (ctolensOn && briefing && briefing.executive_briefing) {
        const summary = briefing.executive_briefing.executive_summary || '';
        subtitle = summary.length > 120 ? summary.slice(0, 117) + '...' : summary;
    } else {
        const eb = briefing && briefing.executive_briefing;
        if (eb && eb.headline) {
            subtitle = eb.headline;
        }
    }
    if (staleness && staleness.is_stale) {
        subtitle += ' · may be outdated';
    }
    return subtitle || 'Executive narrative and signals';
}

function renderBriefingPanelBody(briefing, emptyMessage, ctolensMode, staleness, diagnostics) {
    if (ctolensMode) {
        return renderCtolenBriefingPanelBody(briefing, emptyMessage, staleness, diagnostics);
    }
    if (!briefing) {
        return '<div class="bg-gray-50 border border-gray-200 rounded-lg p-4 text-sm text-gray-600">' +
            (emptyMessage || 'No briefing yet. Import data or click Refresh.') +
            ' <button type="button" onclick="refreshAttentionBriefing()" class="text-blue-600 hover:underline ml-2">Refresh</button></div>';
    }
    const eb = briefing.executive_briefing || {};
    let html = '<div class="flex justify-end mb-3"><button type="button" onclick="refreshAttentionBriefing()" class="text-sm text-blue-600 hover:underline">Refresh briefing</button></div>';
    if (eb.bullets && eb.bullets.length) {
        html += '<ul class="text-sm text-gray-700 list-disc ml-4 mb-4">';
        eb.bullets.forEach(function(b) { html += '<li>' + b + '</li>'; });
        html += '</ul>';
    }
    if (briefing.cto_narrative) {
        html += '<p class="text-sm text-gray-700 bg-gray-50 border border-gray-200 rounded p-3 mb-4">' + briefing.cto_narrative + '</p>';
    }
    const risks = briefing.risk_signals || [];
    const opps = briefing.opportunity_signals || [];
    html += '<div class="grid grid-cols-1 lg:grid-cols-2 gap-4">';
    html += '<div><h4 class="text-sm font-bold text-red-700 mb-2">Risk Signals (' + risks.length + ')</h4>';
    if (!risks.length) {
        html += '<div class="text-xs text-green-700 bg-green-50 rounded p-2">No risks flagged</div>';
    } else {
        risks.slice(0, 5).forEach(function(r) {
            const c = _pfSeverityColor(r.severity || 'warning');
            html += '<div class="text-xs border-l-2 border-' + c + '-400 pl-2 mb-2 text-gray-700">' + (r.detail || r.title) + '</div>';
        });
    }
    html += '</div>';
    html += '<div><h4 class="text-sm font-bold text-green-700 mb-2">Opportunities (' + opps.length + ')</h4>';
    if (!opps.length) {
        html += '<div class="text-xs text-gray-500 bg-gray-50 rounded p-2">None identified</div>';
    } else {
        opps.slice(0, 5).forEach(function(o) {
            html += '<div class="text-xs border-l-2 border-green-400 pl-2 mb-2 text-gray-700">' + (o.detail || o.title) + '</div>';
        });
    }
    html += '</div></div>';
    if (briefing.generated_at) {
        html += '<div class="text-xs text-gray-400 mt-3">Generated ' + new Date(briefing.generated_at).toLocaleString() + '</div>';
    }
    html += renderCtolenDiagnosticsPanel(diagnostics);
    if (briefing.generated_at) {
        html += '<div class="text-xs text-gray-400 mt-3">Generated ' + new Date(briefing.generated_at).toLocaleString();
        if (briefing.metrics_fetched) {
            html += ' · live metrics included';
        } else {
            html += ' · assignment data only';
        }
        html += '</div>';
    }
    return html;
}

function renderExecutiveFocusBlock(focus) {
    if (!focus || !focus.do_first) return '';
    let html = '<section class="mb-5 bg-indigo-50 border border-indigo-200 rounded-lg p-4">';
    html += '<h4 class="text-sm font-bold text-indigo-900 mb-3">Where To Spend The Next Hour</h4>';
    html += '<dl class="space-y-2 text-sm">';
    html += '<div><dt class="font-semibold text-gray-700">Biggest risk</dt><dd class="text-gray-800 mt-0.5">' + _pfEscapeHtml(focus.biggest_risk) + '</dd></div>';
    html += '<div><dt class="font-semibold text-gray-700">Biggest opportunity</dt><dd class="text-gray-800 mt-0.5">' + _pfEscapeHtml(focus.biggest_opportunity) + '</dd></div>';
    html += '<div><dt class="font-semibold text-gray-700">Do first</dt><dd class="text-gray-900 mt-0.5 font-medium">' + _pfEscapeHtml(focus.do_first) + '</dd></div>';
    html += '<div><dt class="font-semibold text-gray-700">Why</dt><dd class="text-gray-700 mt-0.5">' + _pfEscapeHtml(focus.why_first_action) + '</dd></div>';
    html += '<div><dt class="font-semibold text-gray-700">Confidence</dt><dd class="text-gray-700 mt-0.5">' + _pfEscapeHtml(focus.confidence_summary) + '</dd></div>';
    html += '</dl></section>';
    return html;
}

function renderCtolenBriefingPanelBody(briefing, emptyMessage, staleness, diagnostics) {
    if (!briefing) {
        return '<div class="bg-gray-50 border border-gray-200 rounded-lg p-4 text-sm text-gray-600">' +
            (emptyMessage || 'Add assignments to generate your CTOLens briefing.') +
            '</div>';
    }

    const eb = briefing.executive_briefing || {};
    let html = renderBriefingStaleBanner(staleness);
    html += renderExecutiveFocusBlock(eb.executive_focus);

    if (eb.executive_summary) {
        html += '<section class="mb-5"><h4 class="text-sm font-bold text-gray-800 mb-2">Executive Summary</h4>';
        html += '<p class="text-sm text-gray-700 bg-blue-50 border border-blue-100 rounded-lg p-3">' +
            _pfEscapeHtml(eb.executive_summary) + '</p></section>';
    }

    const risks = eb.top_risks || [];
    html += '<section class="mb-5"><h4 class="text-sm font-bold text-red-700 mb-2">Top Risks (' + risks.length + ')</h4>';
    if (!risks.length) {
        html += '<div class="text-xs text-green-700 bg-green-50 rounded p-2">No critical or warning risks in supplied signals.</div>';
    } else {
        risks.forEach(function(r) {
            const c = _pfSeverityColor(r.severity || 'warning');
            html += '<div class="text-sm border-l-4 border-' + c + '-400 bg-' + c + '-50 px-3 py-2 mb-2 rounded-r">';
            html += '<span class="text-xs font-semibold uppercase text-' + c + '-700">' + _pfEscapeHtml(r.severity) + '</span> ';
            html += '<span class="font-medium text-gray-800">' + _pfEscapeHtml(r.project_name) + '</span>';
            html += '<div class="text-gray-700 mt-1">' + _pfEscapeHtml(r.summary) + '</div></div>';
        });
    }
    html += '</section>';

    const opps = eb.opportunities || [];
    html += '<section class="mb-5"><h4 class="text-sm font-bold text-green-700 mb-2">Opportunities (' + opps.length + ')</h4>';
    if (!opps.length) {
        html += '<div class="text-xs text-gray-500 bg-gray-50 rounded p-2">None identified from supplied signals.</div>';
    } else {
        opps.forEach(function(o) {
            html += '<div class="text-sm border-l-4 border-green-400 bg-green-50 px-3 py-2 mb-2 rounded-r">';
            html += '<span class="font-medium text-gray-800">' + _pfEscapeHtml(o.project_name) + '</span>';
            html += '<div class="text-gray-700 mt-1">' + _pfEscapeHtml(o.summary) + '</div></div>';
        });
    }
    html += '</section>';

    const actions = eb.recommended_actions || [];
    html += '<section class="mb-5"><h4 class="text-sm font-bold text-indigo-700 mb-2">Recommended Actions (' + actions.length + ')</h4>';
    if (!actions.length) {
        html += '<div class="text-xs text-gray-500 bg-gray-50 rounded p-2">No recommendations from current signals.</div>';
    } else {
        actions.forEach(function(a, idx) {
            const pc = a.priority === 'high' ? 'red' : (a.priority === 'medium' ? 'yellow' : 'gray');
            html += '<div class="border border-gray-200 rounded-lg p-3 mb-2 bg-white">';
            html += '<div class="flex items-start justify-between gap-2">';
            html += '<div class="min-w-0 flex-1">';
            html += '<div class="text-sm font-semibold text-gray-800">' + (idx + 1) + '. ' + _pfEscapeHtml(a.title) + '</div>';
            html += '<div class="text-xs text-gray-500 mt-0.5">' + _pfEscapeHtml(a.project_name) +
                ' \u2022 impact ' + a.impact_score + ' \u2022 ' + _pfEscapeHtml(a.priority) + '</div>';
            html += '<p class="text-sm text-gray-700 mt-1">' + _pfEscapeHtml(a.description) + '</p>';
            if (a.why) {
                html += '<p class="text-xs text-gray-600 mt-1"><span class="font-semibold">Why:</span> ' + _pfEscapeHtml(a.why) + '</p>';
            }
            if (a.source_signal_ids && a.source_signal_ids.length) {
                html += '<p class="text-xs text-gray-400 mt-0.5">Source: ' + _pfEscapeHtml(a.source_signal_ids.join(', ')) + '</p>';
            }
            html += '</div>';
            html += '<div class="flex flex-col gap-1 shrink-0">';
            html += '<button type="button" class="text-xs bg-green-600 text-white px-2 py-1 rounded hover:bg-green-700" ';
            html += 'data-rec-id="' + _pfEscapeHtml(a.recommendation_id) + '" data-rec-title="' + _pfEscapeHtml(a.title) + '" ';
            html += 'onclick="submitRecommendationFeedback(this.getAttribute(\'data-rec-id\'), this.getAttribute(\'data-rec-title\'), \'accepted\')">Accept</button>';
            html += '<button type="button" class="text-xs bg-gray-200 text-gray-800 px-2 py-1 rounded hover:bg-gray-300" ';
            html += 'data-rec-id="' + _pfEscapeHtml(a.recommendation_id) + '" data-rec-title="' + _pfEscapeHtml(a.title) + '" ';
            html += 'onclick="submitRecommendationFeedback(this.getAttribute(\'data-rec-id\'), this.getAttribute(\'data-rec-title\'), \'dismissed\')">Dismiss</button>';
            html += '</div></div></div>';
        });
    }
    html += '</section>';

    const projects = eb.projects_requiring_attention || [];
    html += '<section class="mb-5"><h4 class="text-sm font-bold text-amber-700 mb-2">Projects Requiring Attention (' + projects.length + ')</h4>';
    if (!projects.length) {
        html += '<div class="text-xs text-green-700 bg-green-50 rounded p-2">No medium/high severity project signals.</div>';
    } else {
        projects.forEach(function(p) {
            const c = _pfSeverityColor(p.highest_severity || 'warning');
            html += '<div class="border border-' + c + '-200 bg-' + c + '-50 rounded-lg p-3 mb-2">';
            html += '<div class="text-sm font-semibold text-gray-800">' + _pfEscapeHtml(p.project_name) +
                ' <span class="text-xs font-normal text-' + c + '-700">(' + p.signal_count + ' signal(s), ' +
                _pfEscapeHtml(p.highest_severity) + ')</span></div>';
            if (p.summaries && p.summaries.length) {
                html += '<ul class="text-xs text-gray-700 list-disc ml-4 mt-1">';
                p.summaries.forEach(function(s) {
                    html += '<li>' + _pfEscapeHtml(s) + '</li>';
                });
                html += '</ul>';
            }
            html += '</div>';
        });
    }
    html += '</section>';

    const conf = eb.confidence_assessment || {};
    html += '<section class="mb-4"><h4 class="text-sm font-bold text-gray-800 mb-2">Confidence Assessment</h4>';
    html += '<div class="text-sm text-gray-700 bg-gray-50 border border-gray-200 rounded-lg p-3">';
    html += '<div class="text-xs font-semibold uppercase text-gray-500 mb-1">Overall: ' + _pfEscapeHtml(conf.overall_level || 'unknown') + '</div>';
    html += '<p>' + _pfEscapeHtml(conf.narrative || '') + '</p></div></section>';

    const fb = briefing.feedback_summary || {};
    const metaParts = [];
    if (briefing.generated_at) {
        metaParts.push('Generated ' + new Date(briefing.generated_at).toLocaleString());
    }
    if (eb.generation_mode) {
        metaParts.push('Mode: ' + eb.generation_mode);
    }
    if (briefing.signals) {
        metaParts.push(briefing.signals.length + ' signal(s)');
    }
    if (fb.total) {
        metaParts.push('Feedback: ' + fb.accepted + ' accepted, ' + fb.dismissed + ' dismissed');
    }
    if (metaParts.length) {
        html += '<div class="text-xs text-gray-400 mt-2">' + metaParts.join(' \u2022 ') + '</div>';
    }
    return html;
}

async function submitRecommendationFeedback(recommendationId, title, status) {
    if (!currentWorkspace || !recommendationId) return;
    let reason = null;
    if (status === 'dismissed') {
        reason = window.prompt('Reason for dismissing (optional):', '');
        if (reason === null) return;
        reason = reason.trim() || null;
    }
    try {
        const resp = await authFetch('/api/workspaces/' + encodeURIComponent(currentWorkspace) + '/ctolens/recommendations/feedback', {
            method: 'POST',
            headers: Object.assign({ 'Content-Type': 'application/json' }, getAuthHeaders()),
            body: JSON.stringify({
                recommendation_id: recommendationId,
                title: title,
                status: status,
                reason: reason
            })
        });
        if (!resp.ok) {
            const err = await resp.json().catch(function() { return {}; });
            throw new Error(err.error || ('HTTP ' + resp.status));
        }
        showNotification(status === 'accepted' ? 'Recommendation accepted' : 'Recommendation dismissed', 'success');
        await reloadBriefingPanelOnly();
    } catch (e) {
        console.warn('Feedback failed:', e);
        showNotification('Could not save feedback: ' + e.message, 'error');
    }
}

function renderPortfolioDetailsBody(data) {
    const bv = data.budget_variance || {};
    const ch = data.connector_health || {};
    const rank = data.assignment_ranking || [];
    let html = '';

    html += '<div class="mb-6"><h4 class="text-md font-bold text-gray-800 mb-3">\uD83D\uDCB0 Budget Variance</h4>';
    const pvp = bv.portfolio_variance_pct;
    const pvColor = pvp == null ? 'gray' : (pvp > 20 ? 'red' : (pvp > 10 ? 'yellow' : 'green'));
    html += '<div class="mb-3 text-sm">Portfolio: <span class="font-bold">' + _pfMoney(bv.portfolio_actual_burn) + '</span> vs target <span class="font-bold">' + _pfMoney(bv.portfolio_target_burn) + '</span> ';
    html += '<span class="text-' + pvColor + '-600 font-semibold">(' + (pvp == null ? 'no targets' : (pvp > 0 ? '+' : '') + pvp + '%') + ')</span></div>';
    if (bv.assignments && bv.assignments.length) {
        html += '<table class="min-w-full text-sm"><tbody>';
        bv.assignments.forEach(function(r) {
            const rc = r.status === 'critical' ? 'red' : (r.status === 'over' ? 'yellow' : 'green');
            html += '<tr class="border-b border-gray-100"><td class="py-1 pr-2 text-gray-800">' + r.name + '</td>';
            html += '<td class="py-1 pr-2 text-right text-gray-600">' + _pfMoney(r.actual_monthly_burn) + ' / ' + _pfMoney(r.target_monthly_burn) + '</td>';
            html += '<td class="py-1 text-right text-' + rc + '-600 font-semibold">' + (r.variance_pct > 0 ? '+' : '') + r.variance_pct + '%</td></tr>';
        });
        html += '</tbody></table>';
    } else {
        html += '<div class="text-sm text-gray-500">No assignments have a target monthly burn set.</div>';
    }
    html += '</div>';

    html += '<div class="mb-6"><h4 class="text-md font-bold text-gray-800 mb-3">\uD83D\uDD0C Connector Health <span class="text-sm font-normal text-gray-500">(' + (ch.readiness_pct == null ? 'n/a' : ch.readiness_pct + '% ready') + ')</span></h4>';
    const cmap = { ready: 'green', degraded: 'yellow', needs_credentials: 'red', disabled: 'gray' };
    let anyConn = false;
    (ch.connectors || []).forEach(function(c) {
        if (c.enabled_count === 0) return;
        anyConn = true;
        const col = cmap[c.status] || 'gray';
        html += '<div class="flex items-center justify-between py-1 border-b border-gray-100">';
        html += '<span class="text-sm font-medium text-gray-700 capitalize">' + c.connector + '</span>';
        html += '<span class="text-xs px-2 py-1 rounded-full bg-' + col + '-100 text-' + col + '-800">' + c.ready_count + '/' + c.enabled_count + ' ready \u2022 ' + c.status.replace('_', ' ') + '</span></div>';
    });
    if (!anyConn) html += '<div class="text-sm text-gray-500">No connectors enabled across active assignments.</div>';
    html += '</div>';

    html += '<div><h4 class="text-md font-bold text-gray-800 mb-3">\uD83D\uDCCA Assignment Ranking <span class="text-sm font-normal text-gray-500">(by attention need)</span></h4>';
    if (rank.length === 0) {
        html += '<div class="text-sm text-gray-500">No active assignments.</div>';
    } else {
        html += '<div class="overflow-x-auto"><table class="min-w-full text-sm"><thead><tr class="bg-gray-50 text-left text-gray-600">';
        html += '<th class="px-3 py-2">#</th><th class="px-3 py-2">Assignment</th><th class="px-3 py-2">Level</th><th class="px-3 py-2 text-right">Burn</th><th class="px-3 py-2 text-right">Variance</th><th class="px-3 py-2 text-right">Connectors</th>';
        html += '</tr></thead><tbody>';
        rank.forEach(function(r, i) {
            const lc = _pfBandColor(r.attention_level);
            html += '<tr class="border-b border-gray-100"><td class="px-3 py-2 text-gray-400">' + (i + 1) + '</td>';
            html += '<td class="px-3 py-2 text-gray-800 font-medium">' + r.name + '</td>';
            html += '<td class="px-3 py-2"><span class="text-xs px-2 py-1 rounded-full bg-' + lc + '-100 text-' + lc + '-800 capitalize">' + r.attention_level.replace('_', ' ') + '</span></td>';
            html += '<td class="px-3 py-2 text-right text-gray-700">' + _pfMoney(r.monthly_burn) + '</td>';
            html += '<td class="px-3 py-2 text-right text-gray-700">' + (r.variance_pct == null ? '\u2014' : (r.variance_pct > 0 ? '+' : '') + r.variance_pct + '%') + '</td>';
            html += '<td class="px-3 py-2 text-right text-gray-700">' + r.ready_connectors + '/' + r.enabled_connectors + '</td></tr>';
        });
        html += '</tbody></table></div>';
    }
    html += '</div>';
    return html;
}

function renderOverviewPanelsLayout(portfolioData, briefingData, portfolioOn, attentionOn, ctolensOn) {
    let html = '';
    const briefingStaleness = briefingData && briefingData.staleness;
    const attentionItems = collectAttentionItems(portfolioData, briefingData, ctolensOn);
    const attentionCount = attentionItems.length;
    const attentionExpanded = attentionCount > 0;
    const briefingOn = ctolensOn || attentionOn;

    if (portfolioOn || briefingOn) {
        html += renderOverviewCollapsible(
            'attention',
            '\uD83D\uDEA8 Needs Attention' + (attentionCount ? ' (' + attentionCount + ')' : ''),
            attentionCount ? 'Items requiring your action' : 'All clear',
            renderAttentionItemsBody(attentionItems),
            attentionExpanded
        );
    }

    if (portfolioOn && portfolioData && !portfolioData.error) {
        const briefing = briefingData && briefingData.briefing;
        const h = portfolioData.health_score || {};
        const band = (h.band || 'healthy').replace('_', ' ');
        let statusLabel = band;
        if (ctolensOn && briefing && briefing.executive_briefing) {
            const conf = briefing.executive_briefing.confidence_assessment || {};
            statusLabel = (conf.overall_level || band) + ' confidence';
        } else if (briefing && briefing.portfolio_status) {
            statusLabel = briefing.portfolio_status;
        }
        html += renderOverviewCollapsible(
            'health',
            '\uD83E\uDDED Portfolio Health',
            'Score ' + (h.overall_score != null ? h.overall_score : '\u2014') + '/100 \u2022 ' + statusLabel,
            renderPortfolioHealthBody(portfolioData, briefing),
            true
        );
        html += renderOverviewCollapsible(
            'details',
            '\uD83D\uDCCA Portfolio Details',
            'Budget variance, connectors, assignment ranking',
            renderPortfolioDetailsBody(portfolioData),
            false
        );
    } else if (portfolioOn && portfolioData && portfolioData.error) {
        html += '<div class="bg-yellow-50 border border-yellow-200 text-yellow-800 px-4 py-3 rounded-lg mb-4">Portfolio dashboard unavailable: ' + portfolioData.error + '</div>';
    }

    if (briefingOn) {
        const briefing = briefingData && briefingData.briefing;
        const briefingSubtitle = formatCtolenRunHeader(briefingData, briefing, ctolensOn, briefingStaleness);
        const exportBtn = briefingOn && (briefing || ctolensOn)
            ? '<button type="button" id="briefing-share-btn" onclick="shareBriefingReport()" class="text-xs sm:text-sm bg-emerald-600 text-white px-2 sm:px-3 py-1.5 rounded-lg hover:bg-emerald-700 whitespace-nowrap">Share</button>'
            + '<button type="button" id="briefing-export-pdf-btn" onclick="exportBriefingPdf()" class="text-xs sm:text-sm bg-blue-600 text-white px-2 sm:px-3 py-1.5 rounded-lg hover:bg-blue-700 whitespace-nowrap">PDF</button>'
            : '';
        const briefingTitle = ctolensOn ? '\uD83C\uDFAF CTOLens Daily Briefing' : '\uD83C\uDFAF Daily CTO Briefing';
        html += renderOverviewCollapsible(
            'briefing',
            briefingTitle,
            briefingSubtitle,
            renderBriefingPanelBody(briefing, briefingData && briefingData.message, ctolensOn, briefingData && briefingData.staleness, briefingData && briefingData.diagnostics),
            false,
            exportBtn
        );
    }

    return html;
}

async function loadOverviewPanels() {
    const root = document.getElementById('overview-panels-root');
    if (!root) return;
    try {
        const flagsResp = await fetch('/api/feature-flags');
        const flags = await flagsResp.json();
        const portfolioOn = flags && flags.portfolio_dashboard;
        const ctolensOn = flags && flags.ctolens_briefing;
        const attentionOn = flags && flags.attention_engine;
        const briefingOn = ctolensOn || attentionOn;
        if (!portfolioOn && !briefingOn) {
            root.innerHTML = '';
            return;
        }
        if (!currentWorkspace) {
            root.innerHTML = '';
            return;
        }

        root.innerHTML = '<div class="text-sm text-gray-500 p-4">Loading overview...</div>';

        let portfolioData = null;
        let briefingData = null;
        const tasks = [];

        if (portfolioOn) {
            tasks.push(
                fetch('/api/portfolio/summary?workspace_id=' + encodeURIComponent(currentWorkspace), { headers: getAuthHeaders() })
                    .then(function(resp) {
                        if (resp.status === 403) return null;
                        return resp.json();
                    })
                    .then(function(d) { portfolioData = d; })
            );
        }
        if (ctolensOn) {
            tasks.push(
                authFetch('/api/workspaces/' + encodeURIComponent(currentWorkspace) + '/ctolens/briefing')
                    .then(function(resp) {
                        if (resp.status === 403) return null;
                        return resp.json();
                    })
                    .then(function(d) { briefingData = d; })
            );
        } else if (attentionOn) {
            tasks.push(
                authFetch('/api/workspaces/' + encodeURIComponent(currentWorkspace) + '/attention/briefing')
                    .then(function(resp) {
                        if (resp.status === 403) return null;
                        return resp.json();
                    })
                    .then(function(d) { briefingData = d; })
            );
        }
        await Promise.all(tasks);

        root.innerHTML = renderOverviewPanelsLayout(portfolioData, briefingData, portfolioOn, attentionOn, ctolensOn);
        if (briefingData && briefingData.briefing) {
            trackInsightViewed('briefing');
        }
    } catch (e) {
        console.warn('Overview panels load failed:', e);
        root.innerHTML = '';
    }
}

async function loadPortfolioDashboard() {
    return loadOverviewPanels();
}

function _pfMoney(n) { return '$' + (Number(n) || 0).toLocaleString(); }
function _pfBandColor(band) { return band === 'healthy' ? 'green' : (band === 'at_risk' ? 'yellow' : 'red'); }
function _pfSeverityColor(sev) { return sev === 'critical' ? 'red' : (sev === 'warning' ? 'yellow' : 'blue'); }

function generateOverviewContent(assignments) {
    // Calculate statistics
    const activeCount = assignments.filter(a => a.status === 'active').length;
    const completedCount = assignments.filter(a => a.status === 'completed').length;
    const archivedCount = assignments.filter(a => a.status === 'archived').length;
    const totalTeamSize = assignments.reduce((sum, a) => sum + (a.team_size || 0), 0);
    const totalBurnRate = assignments.reduce((sum, a) => sum + (a.monthly_burn_rate || 0), 0);
    
    let html = '<div id="overview-panels-root" class="mb-8"></div>';
    html += '<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">';
    
    // Status Cards
    html += '<div class="bg-green-50 border border-green-200 rounded-lg p-4">';
    html += '<div class="flex items-center">';
    html += '<div class="text-3xl mr-3">🟢</div>';
    html += '<div>';
    html += '<h3 class="text-lg font-semibold text-green-800">Active</h3>';
    html += '<p class="text-2xl font-bold text-green-600">' + activeCount + '</p>';
    html += '</div>';
    html += '</div></div>';
    
    html += '<div class="bg-blue-50 border border-blue-200 rounded-lg p-4">';
    html += '<div class="flex items-center">';
    html += '<div class="text-3xl mr-3">🔵</div>';
    html += '<div>';
    html += '<h3 class="text-lg font-semibold text-blue-800">Completed</h3>';
    html += '<p class="text-2xl font-bold text-blue-600">' + completedCount + '</p>';
    html += '</div>';
    html += '</div></div>';
    
    html += '<div class="bg-yellow-50 border border-yellow-200 rounded-lg p-4">';
    html += '<div class="flex items-center">';
    html += '<div class="text-3xl mr-3">🟡</div>';
    html += '<div>';
    html += '<h3 class="text-lg font-semibold text-yellow-800">Archived</h3>';
    html += '<p class="text-2xl font-bold text-yellow-600">' + archivedCount + '</p>';
    html += '</div>';
    html += '</div></div>';
    
    html += '<div class="bg-purple-50 border border-purple-200 rounded-lg p-4">';
    html += '<div class="flex items-center">';
    html += '<div class="text-3xl mr-3">👥</div>';
    html += '<div>';
    html += '<h3 class="text-lg font-semibold text-purple-800">Total Team</h3>';
    html += '<p class="text-2xl font-bold text-purple-600">' + totalTeamSize + '</p>';
    html += '</div>';
    html += '</div></div>';
    
    html += '</div>';
    
    // Assignments Summary Table
    html += '<div class="bg-white rounded-lg shadow p-6">';
    html += '<h3 class="text-xl font-bold text-gray-800 mb-4">📋 All Assignments</h3>';
    html += '<div class="overflow-x-auto">';
    html += '<table class="min-w-full table-auto">';
    html += '<thead><tr class="bg-gray-50">';
    html += '<th class="px-4 py-2 text-left text-sm font-medium text-gray-700">Name</th>';
    html += '<th class="px-4 py-2 text-left text-sm font-medium text-gray-700">Status</th>';
    html += '<th class="px-4 py-2 text-left text-sm font-medium text-gray-700">Team Size</th>';
    html += '<th class="px-4 py-2 text-left text-sm font-medium text-gray-700">Monthly Burn</th>';
    html += '<th class="px-4 py-2 text-left text-sm font-medium text-gray-700">Services</th>';
    html += '<th class="px-4 py-2 text-left text-sm font-medium text-gray-700">Action</th>';
    html += '</tr></thead><tbody>';
    
    assignments.forEach(assignment => {
        const statusColor = assignment.status === 'active' ? 'green' : 
                           assignment.status === 'completed' ? 'blue' : 'yellow';
        const statusEmoji = assignment.status === 'active' ? '🟢' : 
                           assignment.status === 'completed' ? '🔵' : '🟡';
        
        const selectedClass = selectedAssignmentId === assignment.id ? ' bg-blue-100 border-blue-200' : '';
        html += '<tr class="border-b border-gray-200 hover:bg-blue-50 cursor-pointer' + selectedClass + '" onclick="selectAssignment(\'' + assignment.id + '\', \'' + (assignment.name || assignment.id) + '\')">';
        html += '<td class="px-4 py-3">';
        html += '<div class="font-medium text-gray-900">' + (assignment.name || assignment.id) + (selectedAssignmentId === assignment.id ? ' <span class="text-blue-600 text-xs">✓ Selected</span>' : '') + '</div>';
        html += '<div class="text-sm text-gray-500">' + (assignment.description || '') + '</div>';
        html += '</td>';
        html += '<td class="px-4 py-3">';
        html += '<span class="inline-flex items-center px-2 py-1 bg-' + statusColor + '-100 text-' + statusColor + '-800 text-xs rounded-full">';
        html += statusEmoji + ' ' + (assignment.status || 'unknown');
        html += '</span></td>';
        html += '<td class="px-4 py-3 text-sm text-gray-900">' + (assignment.team_size || 'N/A') + '</td>';
        html += '<td class="px-4 py-3 text-sm text-gray-900">$' + (assignment.monthly_burn_rate || 0).toLocaleString() + '</td>';
        html += '<td class="px-4 py-3">';
        
        if (assignment.metrics_config) {
            const services = [];
            if (assignment.metrics_config.github?.enabled) services.push('GitHub');
            if (assignment.metrics_config.jira?.enabled) services.push('Jira');
            if (assignment.metrics_config.aws?.enabled) services.push('AWS');
            if (assignment.metrics_config.railway?.enabled) services.push('Railway');
            
            services.forEach(service => {
                const color = service === 'GitHub' ? 'purple' : 
                             service === 'Jira' ? 'blue' : 
                             service === 'AWS' ? 'orange' : 'green';
                html += '<span class="inline-block px-2 py-1 bg-' + color + '-100 text-' + color + '-800 text-xs rounded mr-1 mb-1">' + service + '</span>';
            });
        }
        
        html += '</td>';
        html += '<td class="px-4 py-3">';
        html += '<button onclick="showTab(' + "'assignment-" + assignment.id + "'" + ')" class="bg-blue-600 text-white px-3 py-1 text-sm rounded hover:bg-blue-700">View Details</button>';
        html += '</td>';
        html += '</tr>';
    });
    
    html += '</tbody></table></div></div>';
    
    return html;
}

function generateAssignmentContent(assignment) {
    let html = '<div class="bg-white rounded-lg shadow-lg p-6">';
    html += '<div class="flex justify-between items-start mb-4">';
    html += '<div>';
    html += '<h2 class="text-2xl font-bold text-gray-800">' + (assignment.name || assignment.id || 'Unknown Assignment') + '</h2>';
    html += '<p class="text-gray-600">ID: ' + (assignment.id || 'N/A') + '</p>';
    if (assignment.description) {
        html += '<p class="text-gray-700 mt-2">' + assignment.description + '</p>';
    }
    html += '</div>';
    
    html += '<div class="flex items-center space-x-2">';
    // Status badge  
    const statusColor = assignment.status === 'active' ? 'green' : 
                      assignment.status === 'completed' ? 'blue' : 'yellow';
    html += '<span class="px-3 py-1 bg-' + statusColor + '-100 text-' + statusColor + '-800 text-sm rounded-full">' + 
            (assignment.status || 'unknown') + '</span>';
    
    // Phase 5A: Basic Assignment Management buttons
    html += '<button onclick="editAssignment(\'' + assignment.id + '\')" class="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs hover:bg-blue-200 ml-2">✏️ Edit</button>';
    html += '<button onclick="toggleAssignmentStatus(\'' + assignment.id + '\')" class="px-2 py-1 bg-yellow-100 text-yellow-700 rounded text-xs hover:bg-yellow-200 ml-1">⏸️ Toggle</button>';
    html += '<button onclick="deleteAssignment(\'' + assignment.id + '\')" class="px-2 py-1 bg-red-100 text-red-700 rounded text-xs hover:bg-red-200 ml-1">🗑️ Delete</button>';
    
    console.log('Assignment management buttons added for:', assignment.id);
    html += '</div>';
    html += '</div>';
    
    // Assignment Details with Basic Metrics Integration - Phase 5B
    html += '<div class="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4 mb-6">';
    html += '<div class="bg-gray-50 rounded p-4">';
    html += '<h4 class="font-semibold text-gray-700 mb-2">👥 Team Size</h4>';
    html += '<p class="text-2xl font-bold text-blue-600">' + (assignment.team_size || 'N/A') + '</p>';
    html += '</div>';
    html += '<div class="bg-gray-50 rounded p-4">';
    html += '<h4 class="font-semibold text-gray-700 mb-2">💰 Monthly Burn</h4>';
    html += '<p class="text-2xl font-bold text-green-600">$' + (assignment.monthly_burn_rate || 0).toLocaleString() + '</p>';
    html += '</div>';
    html += '<div class="bg-gray-50 rounded p-4">';
    html += '<h4 class="font-semibold text-gray-700 mb-2">📅 Duration</h4>';
    html += '<p class="text-sm text-gray-600">Started: ' + (assignment.start_date || 'N/A') + '</p>';
    html += '<p class="text-sm text-gray-600">End: ' + (assignment.end_date || 'Ongoing') + '</p>';
    html += '</div>';
    // Phase 5B: Basic Metrics Integration - Live Metrics Cards
    html += '<div class="bg-gray-50 rounded p-4">';
    html += '<h4 class="font-semibold text-gray-700 mb-2">📊 Metrics</h4>';
    html += '<p id="metrics-' + assignment.id + '" class="text-lg font-bold text-purple-600">Loading...</p>';
    html += '<div class="text-xs text-gray-500 mt-1">Live data</div>';
    html += '</div>';
    html += '<div class="bg-gray-50 rounded p-4">';
    html += '<h4 class="font-semibold text-gray-700 mb-2">⚡ Status</h4>';
    html += '<p class="text-lg font-bold text-emerald-600">' + (assignment.status || 'active').toUpperCase() + '</p>';
    html += '<div class="text-xs text-gray-500 mt-1">Current state</div>';
    html += '</div>';
    html += '</div>';
    
    // Metrics section
    if (assignment.metrics_config) {
        const enabledServices = countEnabledServices(assignment.metrics_config);
        html += '<div class="bg-gray-50 rounded p-4 mb-4">';
        html += '<h3 class="font-semibold text-gray-800 mb-2">📊 Enabled Services (' + enabledServices + ')</h3>';
        html += '<div class="flex flex-wrap gap-2 mb-3">';
        
        if (assignment.metrics_config.github && assignment.metrics_config.github.enabled) {
            html += '<span class="px-2 py-1 bg-purple-100 text-purple-800 text-sm rounded">GitHub</span>';
        }
        if (assignment.metrics_config.jira && assignment.metrics_config.jira.enabled) {
            html += '<span class="px-2 py-1 bg-blue-100 text-blue-800 text-sm rounded">Jira</span>';
        }
        if (assignment.metrics_config.aws && assignment.metrics_config.aws.enabled) {
            html += '<span class="px-2 py-1 bg-orange-100 text-orange-800 text-sm rounded">AWS (Real Data)</span>';
        }
        if (assignment.metrics_config.railway && assignment.metrics_config.railway.enabled) {
            html += '<span class="px-2 py-1 bg-green-100 text-green-800 text-sm rounded">Railway</span>';
        }
        if (assignment.metrics_config.openai && assignment.metrics_config.openai.enabled) {
            html += '<span class="px-2 py-1 bg-purple-100 text-purple-800 text-sm rounded">🤖 OpenAI</span>';
        }
        
        html += '</div>';
        html += '<button data-assignment-id="' + assignment.id + '" ';
        html += 'onclick="loadRealMetrics(this.getAttribute(&quot;data-assignment-id&quot;))" ';
        html += 'class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 transition-colors">';
        html += '🔄 Load All Metrics</button>';
        html += '</div>';
        // Metrics display area (full width, directly under the Load All Metrics button)
        html += '<div id="metrics-display-' + assignment.id + '" class="mt-4"></div>';
    }
    
    // Tech Stack
    if (assignment.team && assignment.team.tech_stack) {
        html += '<div class="bg-gray-50 rounded p-4 mb-4">';
        html += '<h4 class="font-semibold text-gray-700 mb-2">🛠️ Tech Stack</h4>';
        html += '<div class="flex flex-wrap gap-2">';
        assignment.team.tech_stack.forEach(tech => {
            html += '<span class="px-2 py-1 bg-indigo-100 text-indigo-800 text-sm rounded">' + tech + '</span>';
        });
        html += '</div></div>';
    }
    
    html += '</div>';
    
    return html;
}

function connectorMetricsOk(payload) {
    if (!payload) return false;
    if (payload.error) return false;
    if (payload.cost_analysis && payload.cost_analysis.error) return false;
    if (Array.isArray(payload)) {
        return payload.length > 0 && payload.every(item => !item.error);
    }
    return true;
}

function summarizeMetricsPayload(data) {
    const parts = [];
    for (const key of ['github', 'jira', 'aws', 'openai', 'railway']) {
        if (!data[key]) continue;
        const p = data[key];
        if (p.error) {
            parts.push(`${key}: ${p.error}`);
        } else if (p.cost_analysis && p.cost_analysis.error) {
            parts.push(`${key}: ${p.cost_analysis.error}`);
        } else if (Array.isArray(p)) {
            const err = p.find(item => item.error);
            parts.push(err ? `${key}: ${err.error}` : `${key}: ok (${p.length})`);
        } else {
            parts.push(`${key}: ok`);
        }
    }
    return parts.join('; ') || 'no connectors returned data';
}

// Phase 5B: Load basic metrics summary for dashboard cards
async function loadBasicMetrics(assignmentId) {
    const metricsElement = document.getElementById('metrics-' + assignmentId);
    if (!metricsElement) return;
    
    try {
        const response = await authFetch(
            `/api/workspaces/${currentWorkspace}/assignments/${assignmentId}/metrics`
        );
        
        if (!response.ok) {
            if (response.status === 404) {
                metricsElement.innerHTML = '<span class="text-gray-500">No metrics</span>';
                return;
            }
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        console.log(
            `📊 Metrics summary [${assignmentId}]:`,
            summarizeMetricsPayload(data),
            data
        );

        let metricsCount = 0;
        let statusColor = 'text-gray-500';
        
        if (connectorMetricsOk(data.github)) metricsCount++;
        if (connectorMetricsOk(data.jira)) metricsCount++;
        if (connectorMetricsOk(data.aws)) metricsCount++;
        if (connectorMetricsOk(data.openai)) metricsCount++;
        if (connectorMetricsOk(data.railway)) metricsCount++;
        
        if (metricsCount > 0) {
            statusColor = 'text-green-600';
        } else if (Object.keys(data).length > 0) {
            statusColor = 'text-amber-600';
        }
        
        const label = metricsCount > 0
            ? `${metricsCount} active`
            : (Object.keys(data).length ? 'needs config' : 'No metrics');
        metricsElement.innerHTML = `<span class="${statusColor}">${label}</span>`;
        
    } catch (error) {
        console.warn('Failed to load basic metrics for', assignmentId, ':', error);
        metricsElement.innerHTML = '<span class="text-gray-500">No metrics</span>';
    }
}

async function loadRealMetrics(assignmentId) {
    const metricsDiv = document.getElementById('metrics-display-' + assignmentId);
    const loadStarted = Date.now();
    metricsDiv.innerHTML = '<div class="bg-blue-50 p-4 rounded"><div class="loading-spinner"></div><p class="mt-2 text-gray-700">Loading all metrics…</p><p class="text-sm text-gray-500">Calling GitHub, AWS, OpenAI, and other APIs in parallel. This often takes 30–90 seconds.</p></div>';
    
    try {
        const ws = currentWorkspace ? `?workspace_id=${encodeURIComponent(currentWorkspace)}` : '';
        const metricsUrl = '/api/all-metrics/' + assignmentId + ws;
        console.log('🏢 Loading full metrics:', metricsUrl);
        
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 120000);
        const response = await authFetch(metricsUrl, { signal: controller.signal });
        clearTimeout(timeoutId);
        
        if (!response.ok) {
            if (response.status === 404) {
                metricsDiv.innerHTML = '<div class="bg-yellow-100 border border-yellow-400 text-yellow-700 px-4 py-3 rounded">📋 No metrics available yet. Configure connectors in the assignment setup to start collecting metrics.</div>';
                return;
            }
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log(
            `📊 Full metrics [${assignmentId}]:`,
            summarizeMetricsPayload(data),
            data
        );
        
        if (data.error) {
            metricsDiv.innerHTML = '<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">Metrics Error: ' + data.error + '</div>';
            return;
        }
        
        console.log(`📊 Full metrics loaded in ${((Date.now() - loadStarted) / 1000).toFixed(1)}s`);
        displayAllMetrics(data, metricsDiv);
        
    } catch (error) {
        const msg = error.name === 'AbortError'
            ? 'Metrics request timed out after 2 minutes. Try again or disable a slow connector (AWS is often the slowest).'
            : error.message;
        metricsDiv.innerHTML = '<div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">Failed to load metrics: ' + msg + '</div>';
    }
}

function displayAllMetrics(metrics, container) {
    let html = '<div class="bg-gray-50 rounded-lg p-4">';
    html += '<h3 class="text-xl font-bold text-gray-800 mb-4">📊 All Metrics - ' + new Date().toLocaleString() + '</h3>';
    
    // GitHub Metrics
    if (metrics.github && metrics.github.error) {
        html += '<div class="bg-red-100 border border-red-300 text-red-700 p-3 rounded mb-4">';
        html += '🚀 GitHub Error: ' + metrics.github.error;
        html += '</div>';
    } else if (metrics.github && Array.isArray(metrics.github)) {
        html += '<div class="bg-purple-50 border border-purple-200 rounded mb-4">';
        html += '<div class="cursor-pointer p-4 hover:bg-purple-100" onclick="toggleSection(' + "'github-section'" + ')">';
        html += '<h4 class="text-lg font-semibold text-purple-800 flex items-center">';
        html += '<span id="github-section-icon" class="mr-2">▶️</span>';
        html += '🚀 GitHub Repositories (' + metrics.github.length + ')';
        html += '</h4></div>';
        html += '<div id="github-section" class="hidden p-4 pt-0">';
        
        metrics.github.forEach(repo => {
            if (repo.error) {
                html += '<div class="bg-red-100 text-red-700 p-2 rounded mb-2">Error: ' + repo.error + '</div>';
            } else {
                html += '<div class="bg-white p-3 rounded border mb-2">';
                html += '<div class="flex justify-between items-start">';
                html += '<div>';
                html += '<h5 class="font-medium text-gray-800">' + repo.repo_name + '</h5>';
                html += '<div class="text-sm text-gray-600">Language: ' + repo.language + '</div>';
                html += '</div>';
                html += '<div class="text-right text-sm">';
                html += '<div>⭐ ' + repo.stars + ' stars</div>';
                html += '<div>🔄 ' + repo.commits_last_30_days + ' commits (30d)</div>';
                html += '<div>📝 ' + repo.total_prs + ' PRs</div>';
                html += '<div>🚨 ' + repo.open_issues + ' issues</div>';
                html += '</div>';
                html += '</div>';
                html += '</div>';
            }
        });
        
        // GitHub Recommendations
        html += '<div class="bg-purple-100 p-3 rounded mt-3">';
        html += '<h5 class="font-medium text-purple-800 mb-2">🚀 GitHub Development Insights</h5>';
        html += '<ul class="space-y-1 text-xs text-purple-700">';
        
        let totalCommits = 0;
        let totalStars = 0;
        let totalIssues = 0;
        let activeRepos = 0;
        
        metrics.github.forEach(repo => {
            if (!repo.error) {
                totalCommits += repo.commits_last_30_days || 0;
                totalStars += repo.stars || 0;
                totalIssues += repo.open_issues || 0;
                if (repo.commits_last_30_days > 0) activeRepos++;
            }
        });
        
        if (totalCommits < 50) {
            html += '<li>• 🔍 Low commit activity (' + totalCommits + '/month) - consider increasing development velocity</li>';
        } else {
            html += '<li>• ✅ Good development activity (' + totalCommits + ' commits/month)</li>';
        }
        
        if (totalIssues > 20) {
            html += '<li>• ⚠️ High open issue count (' + totalIssues + ') - prioritize technical debt reduction</li>';
        }
        
        if (activeRepos === 0) {
            html += '<li>• 🚨 No active repositories - investigate development process</li>';
        } else {
            html += '<li>• 📈 ' + activeRepos + ' active repositories - maintain code quality standards</li>';
        }
        
        html += '<li>• 📚 Consider implementing automated testing and CI/CD pipelines</li>';
        html += '</ul>';
        html += '</div>';
        
        html += '</div>';
        html += '</div>';
    }
    
    // Jira Metrics
    if (metrics.jira && !metrics.jira.error) {
        html += '<div class="bg-blue-50 border border-blue-200 rounded mb-4">';
        html += '<div class="cursor-pointer p-4 hover:bg-blue-100" onclick="toggleSection(' + "'jira-section'" + ')">';
        html += '<h4 class="text-lg font-semibold text-blue-800 flex items-center">';
        html += '<span id="jira-section-icon" class="mr-2">▶️</span>';
        html += '📋 Jira Project: ' + metrics.jira.project_name;
        html += '</h4></div>';
        html += '<div id="jira-section" class="hidden p-4 pt-0">';
        html += '<div class="grid grid-cols-1 md:grid-cols-3 gap-4">';
        
        html += '<div class="bg-white p-3 rounded border">';
        html += '<div class="text-sm text-gray-600">Total Issues (30d)</div>';
        html += '<div class="text-xl font-bold text-blue-600">' + metrics.jira.total_issues_last_30_days + '</div>';
        html += '</div>';
        
        html += '<div class="bg-white p-3 rounded border">';
        html += '<div class="text-sm text-gray-600">Resolved Issues</div>';
        html += '<div class="text-xl font-bold text-green-600">' + metrics.jira.resolved_issues_last_30_days + '</div>';
        html += '</div>';
        
        html += '<div class="bg-white p-3 rounded border">';
        html += '<div class="text-sm text-gray-600">Resolution Rate</div>';
        html += '<div class="text-xl font-bold text-purple-600">' + metrics.jira.resolution_rate + '%</div>';
        html += '</div>';
        
        html += '</div>';
        
        // Jira Recommendations
        html += '<div class="bg-blue-100 p-3 rounded mt-3">';
        html += '<h5 class="font-medium text-blue-800 mb-2">📋 Project Management Insights</h5>';
        html += '<ul class="space-y-1 text-xs text-blue-700">';
        
        const resolutionRate = metrics.jira.resolution_rate || 0;
        const totalIssues = metrics.jira.total_issues_last_30_days || 0;
        
        if (resolutionRate < 70) {
            html += '<li>• 🔴 Low resolution rate (' + resolutionRate + '%) - review sprint planning and capacity</li>';
        } else if (resolutionRate < 85) {
            html += '<li>• 🟡 Moderate resolution rate (' + resolutionRate + '%) - optimize workflow efficiency</li>';
        } else {
            html += '<li>• 🟢 Excellent resolution rate (' + resolutionRate + '%) - maintain current velocity</li>';
        }
        
        if (totalIssues < 10) {
            html += '<li>• 📉 Low issue creation (' + totalIssues + '/month) - may indicate planning gaps</li>';
        } else if (totalIssues > 50) {
            html += '<li>• 📈 High issue volume (' + totalIssues + '/month) - consider team capacity</li>';
        }
        
        html += '<li>• 🎯 Focus on reducing cycle time and improving story estimation accuracy</li>';
        html += '<li>• 📊 Implement regular retrospectives to identify process improvements</li>';
        html += '</ul>';
        html += '</div>';
        
        html += '</div>';
        html += '</div>';
    } else if (metrics.jira && metrics.jira.error) {
        html += '<div class="bg-red-100 border border-red-300 text-red-700 p-3 rounded mb-4">';
        html += '📋 Jira Error: ' + metrics.jira.error;
        html += '</div>';
    }
    
    // AWS Metrics - Comprehensive Display
    if (metrics.aws && !metrics.aws.error) {
        const awsCost = metrics.aws.cost_analysis?.total_cost_last_30_days || 0;
        const topServices = metrics.aws.cost_analysis?.top_services || {};
        const weeklyTrend = metrics.aws.cost_analysis?.cto_insights?.cost_trend?.weekly_trend || 'unknown';
        
        html += '<div class="bg-orange-50 border border-orange-200 rounded mb-4">';
        html += '<div class="cursor-pointer p-4 hover:bg-orange-100" onclick="toggleSection(' + "'aws-section'" + ')">';
        html += '<h4 class="text-lg font-semibold text-orange-800 flex items-center">';
        html += '<span id="aws-section-icon" class="mr-2">▶️</span>';
        html += '☁️ AWS Infrastructure ($' + awsCost.toFixed(2) + '/month)';
        html += '</h4>';
        
        // AWS Synopsis - Always visible summary
        html += '<div class="mt-3 grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">';
        html += '<div class="bg-white rounded p-2 text-center">';
        html += '<div class="font-bold text-green-600">$' + awsCost.toFixed(2) + '</div>';
        html += '<div class="text-xs text-gray-600">Monthly Cost</div>';
        html += '</div>';
        html += '<div class="bg-white rounded p-2 text-center">';
        html += '<div class="font-bold text-blue-600">' + Object.keys(topServices).length + '</div>';
        html += '<div class="text-xs text-gray-600">Active Services</div>';
        html += '</div>';
        html += '<div class="bg-white rounded p-2 text-center">';
        const trendIcon = weeklyTrend === 'increasing' ? '📈' : weeklyTrend === 'decreasing' ? '📉' : '➡️';
        const trendColor = weeklyTrend === 'increasing' ? 'text-red-600' : 'text-green-600';
        html += '<div class="font-bold ' + trendColor + '">' + trendIcon + '</div>';
        html += '<div class="text-xs text-gray-600">Cost Trend</div>';
        html += '</div>';
        html += '<div class="bg-white rounded p-2 text-center">';
        html += '<div class="font-bold text-purple-600">Click ▶️</div>';
        html += '<div class="text-xs text-gray-600">Expand Details</div>';
        html += '</div>';
        html += '</div>';
        html += '</div>';
        
        // Expandable detailed sections
        html += '<div id="aws-section" class="hidden p-4 pt-0">';
        
        // 1. Top Services Breakdown (expandable)
        if (Object.keys(topServices).length > 0) {
            html += '<div class="mb-4">';
            html += '<div class="cursor-pointer bg-white border border-orange-200 rounded p-3 hover:bg-orange-50" onclick="toggleSection(' + "'aws-services-section'" + ')">';
            html += '<h5 class="font-semibold text-orange-800 flex items-center">';
            html += '<span id="aws-services-section-icon" class="mr-2">▶️</span>';
            html += '💰 Top Services by Cost (' + Object.keys(topServices).length + ' services)';
            html += '</h5></div>';
            html += '<div id="aws-services-section" class="hidden p-3 bg-gray-50 rounded-b">';
            
            // Service breakdown with percentages
            Object.entries(topServices).slice(0, 8).forEach(([service, cost]) => {
                const percentage = ((cost / awsCost) * 100).toFixed(1);
                const shortName = service.replace('Amazon ', '').replace('AWS ', '');
                html += '<div class="flex justify-between items-center mb-2 p-2 bg-white rounded">';
                html += '<div>';
                html += '<div class="text-sm font-medium text-gray-800">' + shortName + '</div>';
                html += '<div class="text-xs text-gray-600">' + service + '</div>';
                html += '</div>';
                html += '<div class="text-right">';
                html += '<div class="text-sm font-bold text-green-600">$' + parseFloat(cost).toFixed(4) + '</div>';
                html += '<div class="text-xs text-gray-500">' + percentage + '%</div>';
                html += '</div>';
                html += '</div>';
            });
            
            html += '</div>';
            html += '</div>';
        }
        
        // 2. Resource Inventory (expandable)
        html += '<div class="mb-4">';
        html += '<div class="cursor-pointer bg-white border border-orange-200 rounded p-3 hover:bg-orange-50" onclick="toggleSection(' + "'aws-resources-section'" + ')">';
        html += '<h5 class="font-semibold text-orange-800 flex items-center">';
        html += '<span id="aws-resources-section-icon" class="mr-2">▶️</span>';
        html += '🖥️ Resource Inventory & Details';
        html += '</h5></div>';
        html += '<div id="aws-resources-section" class="hidden p-3 bg-gray-50 rounded-b">';
        
        // Resource summary cards and detailed information
        if (metrics.aws.resources?.inventory) {
            const inventory = metrics.aws.resources.inventory;
            html += '<div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">';
            
            if (inventory.ec2?.total_instances) {
                html += '<div class="bg-white rounded p-3 text-center">';
                html += '<div class="text-lg font-bold text-blue-600">' + inventory.ec2.total_instances + '</div>';
                html += '<div class="text-xs text-gray-600">EC2 Instances</div>';
                html += '</div>';
            }
            if (inventory.lightsail?.total_instances) {
                html += '<div class="bg-white rounded p-3 text-center">';
                html += '<div class="text-lg font-bold text-purple-600">' + inventory.lightsail.total_instances + '</div>';
                html += '<div class="text-xs text-gray-600">Lightsail</div>';
                html += '</div>';
            }
            if (inventory.rds?.total_databases) {
                html += '<div class="bg-white rounded p-3 text-center">';
                html += '<div class="text-lg font-bold text-green-600">' + inventory.rds.total_databases + '</div>';
                html += '<div class="text-xs text-gray-600">RDS Databases</div>';
                html += '</div>';
            }
            if (inventory.s3?.total_buckets) {
                html += '<div class="bg-white rounded p-3 text-center">';
                html += '<div class="text-lg font-bold text-yellow-600">' + inventory.s3.total_buckets + '</div>';
                html += '<div class="text-xs text-gray-600">S3 Buckets</div>';
                html += '</div>';
            }
            
            html += '</div>';
            
            // Detailed resource information
            if (inventory.lightsail?.details?.length > 0) {
                html += '<div class="mt-4">';
                html += '<h6 class="font-medium text-gray-800 mb-2">💡 Lightsail Instance Details</h6>';
                html += '<div class="space-y-2">';
                inventory.lightsail.details.forEach(instance => {
                    html += '<div class="bg-purple-50 border border-purple-100 rounded p-2 text-xs">';
                    html += '<div class="flex justify-between items-center">';
                    html += '<div>';
                    html += '<div class="font-medium">' + instance.name + ' (' + instance.instance_type + ')</div>';
                    html += '<div class="text-gray-600">State: ' + instance.state + '</div>';
                    html += '</div>';
                    html += '<div class="text-right">';
                    html += '<div class="font-bold text-purple-600">$' + (instance.bundle_details?.monthly_price || 0) + '/mo</div>';
                    html += '<div class="text-gray-500">' + instance.location + '</div>';
                    html += '</div>';
                    html += '</div>';
                    html += '</div>';
                });
                html += '</div>';
                html += '</div>';
            }
            
            if (inventory.ec2?.details?.length > 0) {
                html += '<div class="mt-4">';
                html += '<h6 class="font-medium text-gray-800 mb-2">🖥️ EC2 Instance Details</h6>';
                html += '<div class="space-y-2">';
                inventory.ec2.details.forEach(instance => {
                    html += '<div class="bg-blue-50 border border-blue-100 rounded p-2 text-xs">';
                    html += '<div class="flex justify-between items-center">';
                    html += '<div>';
                    html += '<div class="font-medium">' + instance.instance_id + '</div>';
                    html += '<div class="text-gray-600">' + instance.instance_type + ' - ' + instance.state + '</div>';
                    html += '</div>';
                    html += '<div class="text-right">';
                    html += '<div class="text-blue-600">' + (instance.availability_zone || 'N/A') + '</div>';
                    html += '<div class="text-gray-500">' + (instance.launch_time ? new Date(instance.launch_time).toLocaleDateString() : 'N/A') + '</div>';
                    html += '</div>';
                    html += '</div>';
                    html += '</div>';
                });
                html += '</div>';
                html += '</div>';
            }
            
            if (inventory.s3?.details?.length > 0) {
                html += '<div class="mt-4">';
                html += '<h6 class="font-medium text-gray-800 mb-2">🪣 S3 Bucket Details</h6>';
                html += '<div class="space-y-2">';
                inventory.s3.details.forEach(bucket => {
                    html += '<div class="bg-yellow-50 border border-yellow-100 rounded p-2 text-xs">';
                    html += '<div class="flex justify-between items-center">';
                    html += '<div>';
                    html += '<div class="font-medium">' + bucket.name + '</div>';
                    html += '<div class="text-gray-600">' + bucket.location + '</div>';
                    html += '</div>';
                    html += '<div class="text-right">';
                    html += '<div class="text-yellow-600">' + (bucket.size_readable || '0 B') + '</div>';
                    html += '<div class="text-gray-500">' + (bucket.creation_date ? new Date(bucket.creation_date).toLocaleDateString() : 'N/A') + '</div>';
                    html += '</div>';
                    html += '</div>';
                    html += '</div>';
                });
                html += '</div>';
                html += '</div>';
            }
            
            // Resource optimization suggestions
            const allSuggestions = [
                ...(inventory.lightsail?.optimization_suggestions || []),
                ...(inventory.ec2?.suggestions || []),
                ...(inventory.s3?.suggestions || [])
            ];
            
            if (allSuggestions.length > 0) {
                html += '<div class="mt-4 bg-blue-50 border border-blue-200 rounded p-3">';
                html += '<h6 class="font-medium text-blue-800 mb-2">💡 Optimization Recommendations</h6>';
                html += '<ul class="text-xs text-blue-700 space-y-1">';
                allSuggestions.slice(0, 4).forEach(suggestion => {
                    html += '<li>' + suggestion + '</li>';
                });
                html += '</ul>';
                html += '</div>';
            }
        }
        html += '</div>';
        html += '</div>';
        
        // 3. CTO Recommendations (expandable)
        html += '<div class="mb-4">';
        html += '<div class="cursor-pointer bg-white border border-orange-200 rounded p-3 hover:bg-orange-50" onclick="toggleSection(' + "'aws-cto-section'" + ')">';
        html += '<h5 class="font-semibold text-orange-800 flex items-center">';
        html += '<span id="aws-cto-section-icon" class="mr-2">▶️</span>';
        html += '🎯 CTO Strategic Recommendations';
        html += '</h5></div>';
        html += '<div id="aws-cto-section" class="hidden p-3 bg-gray-50 rounded-b">';
        
        // Smart recommendations based on actual cost
        html += '<div class="space-y-3">';
        
        if (awsCost > 1000) {
            html += '<div class="bg-red-50 border border-red-200 p-3 rounded">';
            html += '<div class="font-medium text-red-800 mb-2">🚨 High Cost Alert</div>';
            html += '<ul class="text-sm text-red-700 space-y-1">';
            html += '<li>• Monthly spend of $' + awsCost.toFixed(2) + ' requires immediate optimization</li>';
            html += '<li>• Prioritize Reserved Instance analysis for steady workloads</li>';
            html += '<li>• Implement aggressive cost controls and monitoring</li>';
            html += '</ul>';
            html += '</div>';
        } else if (awsCost > 100) {
            html += '<div class="bg-yellow-50 border border-yellow-200 p-3 rounded">';
            html += '<div class="font-medium text-yellow-800 mb-2">⚠️ Moderate Spend</div>';
            html += '<ul class="text-sm text-yellow-700 space-y-1">';
            html += '<li>• Monthly spend of $' + awsCost.toFixed(2) + ' - monitor for efficiency opportunities</li>';
            html += '<li>• Review Resource utilization quarterly</li>';
            html += '<li>• Consider cost allocation tags for better tracking</li>';
            html += '</ul>';
            html += '</div>';
        } else {
            html += '<div class="bg-green-50 border border-green-200 p-3 rounded">';
            html += '<div class="font-medium text-green-800 mb-2">✅ Cost Effective</div>';
            html += '<ul class="text-sm text-green-700 space-y-1">';
            html += '<li>• Excellent cost management at $' + awsCost.toFixed(2) + '/month</li>';
            html += '<li>• Maintain current optimization practices</li>';
            html += '<li>• Monitor for any cost trend changes</li>';
            html += '</ul>';
            html += '</div>';
        }
        
        // General recommendations
        html += '<div class="bg-blue-50 border border-blue-200 p-3 rounded">';
        html += '<div class="font-medium text-blue-800 mb-2">📊 General Recommendations</div>';
        html += '<ul class="text-sm text-blue-700 space-y-1">';
        html += '<li>• Set up AWS Budget alerts for anomaly detection</li>';
        html += '<li>• Review top services: ' + Object.keys(topServices).slice(0, 3).join(', ') + '</li>';
        html += '<li>• Implement comprehensive resource tagging strategy</li>';
        html += '<li>• Schedule quarterly cost optimization reviews</li>';
        html += '</ul>';
        html += '</div>';
        
        html += '</div>';
        html += '</div>';
        html += '</div>';
        
        html += '</div>'; // Close expandable section
        html += '</div>'; // Close AWS container
    } else if (metrics.aws && metrics.aws.error) {
        html += '<div class="bg-red-100 border border-red-300 text-red-700 p-3 rounded mb-4">';
        html += '☁️ AWS Error: ' + metrics.aws.error;
        html += '</div>';
    }
    
    // OpenAI Metrics
    if (metrics.openai && !metrics.openai.error) {
        html += '<div class="bg-purple-50 border border-purple-200 rounded mb-4">';
        html += '<div class="cursor-pointer p-4 hover:bg-purple-100" onclick="toggleSection(' + "'openai-section'" + ')">';
        html += '<h4 class="text-lg font-semibold text-purple-800 flex items-center">';
        html += '<span id="openai-section-icon" class="mr-2">▶️</span>';
        html += '🤖 OpenAI API Usage';
        html += '</h4></div>';
        html += '<div id="openai-section" class="hidden p-4 pt-0">';
        
        // Usage Summary
        html += '<div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">';
        html += '<div class="bg-white p-3 rounded border">';
        html += '<div class="text-sm text-gray-600">Tokens Used</div>';
        html += '<div class="text-xl font-bold text-purple-600">' + (metrics.openai.usage_this_month?.tokens_used || 0).toLocaleString() + '</div>';
        html += '</div>';
        
        html += '<div class="bg-white p-3 rounded border">';
        html += '<div class="text-sm text-gray-600">Requests Made</div>';
        html += '<div class="text-xl font-bold text-blue-600">' + (metrics.openai.usage_this_month?.requests_made || 0) + '</div>';
        html += '</div>';
        
        html += '<div class="bg-white p-3 rounded border">';
        html += '<div class="text-sm text-gray-600">Estimated Cost</div>';
        html += '<div class="text-xl font-bold text-green-600">$' + (metrics.openai.usage_this_month?.estimated_cost || 0) + '</div>';
        html += '</div>';
        html += '</div>';
        
        // Models Used
        if (metrics.openai.models_used && metrics.openai.models_used.length > 0) {
            html += '<div class="bg-white p-3 rounded border mb-3">';
            html += '<h5 class="font-medium text-gray-800 mb-2">Models Used</h5>';
            html += '<div class="flex flex-wrap gap-2">';
            metrics.openai.models_used.forEach(model => {
                html += '<span class="px-2 py-1 bg-purple-100 text-purple-800 text-sm rounded">' + model + '</span>';
            });
            html += '</div></div>';
        }
        
        // Dashboard Links
        html += '<div class="bg-white p-3 rounded border mb-3">';
        html += '<h5 class="font-medium text-gray-800 mb-2">Dashboard Links</h5>';
        html += '<div class="space-y-2">';
        html += '<div><a href="' + metrics.openai.dashboard_url + '" target="_blank" class="text-blue-600 hover:underline text-sm">📊 OpenAI Usage Dashboard →</a></div>';
        html += '<div><a href="' + metrics.openai.billing_url + '" target="_blank" class="text-green-600 hover:underline text-sm">💰 Check Account Balance →</a></div>';
        html += '</div></div>';
        
        // Personal Account Notice
        if (metrics.openai.account_type === 'personal') {
            html += '<div class="bg-blue-100 border border-blue-300 p-3 rounded mb-3">';
            html += '<div class="text-sm text-blue-800">';
            html += '<div class="font-medium mb-1">📱 Personal Account Detected</div>';
            if (metrics.openai.usage_notice) {
                html += '<div class="mb-2">' + metrics.openai.usage_notice + '</div>';
            }
            if (metrics.openai.cto_insights && metrics.openai.cto_insights.optimization_recommendations) {
                html += '<div class="font-medium mb-1">Recommendations:</div>';
                html += '<ul class="list-disc list-inside space-y-1">';
                metrics.openai.cto_insights.optimization_recommendations.slice(0, 3).forEach(rec => {
                    html += '<li>' + rec + '</li>';
                });
                html += '</ul>';
            }
            html += '</div></div>';
        }
        
        // Note about account balance (legacy)
        if (metrics.openai.note) {
            html += '<div class="bg-orange-100 p-3 rounded">';
            html += '<div class="text-sm text-orange-700">ℹ️ ' + metrics.openai.note + '</div>';
            html += '</div>';
        }
        
        html += '</div>';
        html += '</div>';
    } else if (metrics.openai && metrics.openai.error) {
        html += '<div class="bg-red-100 border border-red-300 text-red-700 p-3 rounded mb-4">';
        html += '🤖 OpenAI Error: ' + metrics.openai.error;
        html += '</div>';
    }
    
    // Railway would go here when implemented
    
    // CTO Recommendations Section - Comprehensive for all services
    html += '<div class="bg-yellow-50 border border-yellow-200 p-4 rounded">';
    html += '<h4 class="text-lg font-semibold text-yellow-800 mb-3">💡 CTO Strategic Recommendations</h4>';
    html += '<div class="space-y-3 text-sm text-yellow-700">';
    
    // GitHub Recommendations
    if (metrics.github) {
        html += '<div class="bg-white p-3 rounded border">';
        html += '<h5 class="font-medium text-purple-800 mb-2">🚀 GitHub Development Insights</h5>';
        html += '<ul class="space-y-1 text-xs">';
        
        let totalCommits = 0;
        let totalStars = 0;
        let totalIssues = 0;
        let activeRepos = 0;
        
        if (Array.isArray(metrics.github)) {
            metrics.github.forEach(repo => {
                if (!repo.error) {
                    totalCommits += repo.commits_last_30_days || 0;
                    totalStars += repo.stars || 0;
                    totalIssues += repo.open_issues || 0;
                    if (repo.commits_last_30_days > 0) activeRepos++;
                }
            });
        }
        
        if (totalCommits < 50) {
            html += '<li>• 🔍 Low commit activity (' + totalCommits + '/month) - consider increasing development velocity</li>';
        } else {
            html += '<li>• ✅ Good development activity (' + totalCommits + ' commits/month)</li>';
        }
        
        if (totalIssues > 20) {
            html += '<li>• ⚠️ High open issue count (' + totalIssues + ') - prioritize technical debt reduction</li>';
        }
        
        if (activeRepos === 0) {
            html += '<li>• 🚨 No active repositories - investigate development process</li>';
        } else {
            html += '<li>• 📈 ' + activeRepos + ' active repositories - maintain code quality standards</li>';
        }
        
        html += '<li>• 📚 Consider implementing automated testing and CI/CD pipelines</li>';
        html += '</ul></div>';
    }
    
    // Jira Recommendations
    if (metrics.jira && !metrics.jira.error) {
        html += '<div class="bg-white p-3 rounded border">';
        html += '<h5 class="font-medium text-blue-800 mb-2">📋 Project Management Insights</h5>';
        html += '<ul class="space-y-1 text-xs">';
        
        const resolutionRate = metrics.jira.resolution_rate || 0;
        const totalIssues = metrics.jira.total_issues_last_30_days || 0;
        
        if (resolutionRate < 70) {
            html += '<li>• 🔴 Low resolution rate (' + resolutionRate + '%) - review sprint planning and capacity</li>';
        } else if (resolutionRate < 85) {
            html += '<li>• 🟡 Moderate resolution rate (' + resolutionRate + '%) - optimize workflow efficiency</li>';
        } else {
            html += '<li>• 🟢 Excellent resolution rate (' + resolutionRate + '%) - maintain current velocity</li>';
        }
        
        if (totalIssues < 10) {
            html += '<li>• 📉 Low issue creation (' + totalIssues + '/month) - may indicate planning gaps</li>';
        } else if (totalIssues > 50) {
            html += '<li>• 📈 High issue volume (' + totalIssues + '/month) - consider team capacity</li>';
        }
        
        html += '<li>• 🎯 Focus on reducing cycle time and improving story estimation accuracy</li>';
        html += '<li>• 📊 Implement regular retrospectives to identify process improvements</li>';
        html += '</ul></div>';
    }
    
    // AWS Recommendations
    if (metrics.aws && !metrics.aws.error) {
        html += '<div class="bg-white p-3 rounded border">';
        html += '<h5 class="font-medium text-orange-800 mb-2">☁️ Infrastructure Optimization</h5>';
        html += '<ul class="space-y-1 text-xs">';
        
        const monthlyCost = metrics.aws.total_cost_last_30_days || 0;
        const trend = metrics.aws.weekly_trend;
        
        if (monthlyCost > 1000) {
            html += '<li>• 💰 High monthly spend ($' + monthlyCost + ') - prioritize cost optimization</li>';
        } else if (monthlyCost > 100) {
            html += '<li>• 💡 Moderate spend ($' + monthlyCost + ') - monitor for efficiency gains</li>';
        } else {
            html += '<li>• ✅ Cost-effective infrastructure ($' + monthlyCost + '/month)</li>';
        }
        
        if (trend === 'increasing') {
            html += '<li>• 📈 Rising costs - implement immediate cost controls and monitoring</li>';
        } else {
            html += '<li>• 📉 Cost trend stable/decreasing - maintain optimization practices</li>';
        }
        
        html += '<li>• 🔧 Review unutilized resources and consider Reserved Instance savings</li>';
        html += '<li>• 📊 Set up billing alerts and automated cost anomaly detection</li>';
        html += '<li>• 🏷️ Implement comprehensive resource tagging for cost allocation</li>';
        html += '</ul></div>';
    }
    
    // Overall Strategic Recommendations
    html += '<div class="bg-gradient-to-r from-blue-50 to-purple-50 p-3 rounded border border-blue-200">';
    html += '<h5 class="font-medium text-gray-800 mb-2">🎯 Strategic CTO Priorities</h5>';
    html += '<ul class="space-y-1 text-xs text-gray-700">';
    html += '<li>• 📈 <strong>Velocity:</strong> Align development speed with business objectives</li>';
    html += '<li>• 💰 <strong>Cost Efficiency:</strong> Optimize infrastructure spend without compromising performance</li>';
    html += '<li>• 🔄 <strong>Process:</strong> Streamline workflows to reduce cycle time and improve quality</li>';
    html += '<li>• 📊 <strong>Metrics:</strong> Establish KPIs that tie technical performance to business outcomes</li>';
    html += '<li>• 🛡️ <strong>Risk Management:</strong> Balance technical debt with feature delivery</li>';
    html += '</ul></div>';
    
    html += '</div>';
    html += '</div>';
    
    html += '</div>';
    container.innerHTML = html;
}

function displayRealMetrics(metrics, container) {
    let html = '<div class="bg-gray-50 rounded-lg p-4">';
    html += '<h3 class="text-xl font-bold text-gray-800 mb-4">📊 Real AWS Metrics - ' + new Date().toLocaleString() + '</h3>';
    
    // Cost Summary
    html += '<div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">';
    html += '<div class="bg-white p-4 rounded border">';
    html += '<h5 class="font-medium text-gray-800 mb-2">💰 30-Day Total Cost</h5>';
    html += '<div class="text-2xl font-bold text-green-600">$' + (metrics.total_cost_last_30_days || 0) + '</div>';
    html += '<div class="text-sm text-gray-600">' + (metrics.currency || 'USD') + '</div>';
    html += '</div>';
    
    html += '<div class="bg-white p-4 rounded border">';
    html += '<h5 class="font-medium text-gray-800 mb-2">📈 Weekly Trend</h5>';
    html += '<div class="text-lg font-semibold ' + (metrics.weekly_trend === 'increasing' ? 'text-red-600' : 'text-green-600') + '">';
    html += metrics.weekly_trend === 'increasing' ? '📈 Increasing' : '📉 Decreasing';
    html += '</div>';
    html += '<div class="text-sm text-gray-600">Daily Average: $' + (metrics.daily_average || 0) + '</div>';
    html += '</div>';
    
    html += '<div class="bg-white p-4 rounded border">';
    html += '<h5 class="font-medium text-gray-800 mb-2">🔧 Resource Count</h5>';
    let resourceCount = 0;
    if (metrics.inventory) {
        if (metrics.inventory.ec2) resourceCount += metrics.inventory.ec2.total_instances || 0;
        if (metrics.inventory.rds) resourceCount += metrics.inventory.rds.total_databases || 0;
        if (metrics.inventory.s3) resourceCount += metrics.inventory.s3.total_buckets || 0;
        if (metrics.inventory.lightsail) resourceCount += metrics.inventory.lightsail.total_instances || 0;
    }
    html += '<div class="text-lg font-semibold text-blue-600">' + resourceCount + ' Resources</div>';
    html += '<div class="text-sm text-gray-600">Across all services</div>';
    html += '</div>';
    html += '</div>';
    
    // Service Breakdown
    if (metrics.top_services && Object.keys(metrics.top_services).length > 0) {
        html += '<div class="bg-white p-4 rounded border mb-4">';
        html += '<h5 class="font-medium text-gray-800 mb-3">🏷️ Top Services by Cost</h5>';
        html += '<div class="space-y-2">';
        
        for (const [service, cost] of Object.entries(metrics.top_services)) {
            if (cost > 0) {
                html += '<div class="flex justify-between items-center">';
                html += '<span class="text-sm text-gray-700">' + service + '</span>';
                html += '<span class="font-medium text-gray-900">$' + parseFloat(cost).toFixed(2) + '</span>';
                html += '</div>';
            }
        }
        html += '</div></div>';
    }
    
    // CTO Recommendations
    if (metrics.recommendations) {
        html += '<div class="bg-yellow-50 border border-yellow-200 p-4 rounded">';
        html += '<h5 class="font-medium text-yellow-800 mb-3">💡 CTO Optimization Recommendations</h5>';
        html += '<div class="space-y-1 text-sm text-yellow-700">';
        
        metrics.recommendations.slice(0, 10).forEach(rec => {
            html += '<div>' + rec + '</div>';
        });
        html += '</div></div>';
    }
    
    html += '</div>';
    container.innerHTML = html;
}

function countEnabledServices(metricsConfig) {
    if (!metricsConfig) return 0;
    let count = 0;
    if (metricsConfig.github && metricsConfig.github.enabled) count++;
    if (metricsConfig.jira && metricsConfig.jira.enabled) count++;
    if (metricsConfig.aws && metricsConfig.aws.enabled) count++;
    if (metricsConfig.railway && metricsConfig.railway.enabled) count++;
    return count;
}

function toggleSection(sectionId) {
    const section = document.getElementById(sectionId);
    const icon = document.getElementById(sectionId + '-icon');
    
    if (section && icon) {
        if (section.classList.contains('hidden')) {
            section.classList.remove('hidden');
            icon.textContent = '🔽️';
            if (sectionId === 'overview-briefing-body') {
                trackInsightViewed('briefing');
            }
        } else {
            section.classList.add('hidden');
            icon.textContent = '▶️';
        }
    }
}
