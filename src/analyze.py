from __future__ import annotations

import argparse
import base64
import html
from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = {
    "date", "channel", "carrier", "state", "orders", "revenue",
    "freight_cost", "avg_delivery_days", "on_time_orders", "returns",
    "cancelled_orders", "support_tickets",
}

TARGETS = {
    "sla": 0.92,
    "return_rate": 0.08,
    "cancellation_rate": 0.04,
    "freight_share": 0.12,
    "tickets_per_100": 6.0,
}


def load_data(path: Path) -> tuple[pd.DataFrame, dict[str, int]]:
    frame = pd.read_csv(path)
    missing = REQUIRED_COLUMNS.difference(frame.columns)
    if missing:
        raise ValueError("Colunas obrigatórias ausentes: " + ", ".join(sorted(missing)))

    original_rows = len(frame)
    duplicate_rows = int(frame.duplicated().sum())
    frame = frame.drop_duplicates().copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    numeric = [
        "orders", "revenue", "freight_cost", "avg_delivery_days",
        "on_time_orders", "returns", "cancelled_orders", "support_tickets",
    ]
    for column in numeric:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    invalid = frame[["date", *numeric]].isna().any(axis=1)
    if invalid.any():
        lines = ", ".join(str(index + 2) for index in frame.index[invalid])
        raise ValueError(f"Existem datas ou números inválidos nas linhas: {lines}")
    if (frame["orders"] <= 0).any():
        raise ValueError("orders deve conter apenas valores positivos.")
    for column in ["on_time_orders", "returns", "cancelled_orders"]:
        if (frame[column] > frame["orders"]).any():
            raise ValueError(f"{column} não pode ser maior que orders.")

    quality = {
        "received": original_rows,
        "valid": len(frame),
        "duplicates": duplicate_rows,
        "columns": len(frame.columns),
    }
    return frame, quality


def money(value: float) -> str:
    formatted = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatted}"


def percent(value: float) -> str:
    return f"{value * 100:.1f}%".replace(".", ",")


def decimal(value: float) -> str:
    return f"{value:.1f}".replace(".", ",")


def integer(value: float) -> str:
    return f"{int(value):,}".replace(",", ".")


def image_data(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def metrics(frame: pd.DataFrame) -> dict[str, float]:
    orders = float(frame["orders"].sum())
    revenue = float(frame["revenue"].sum())
    return {
        "orders": orders,
        "revenue": revenue,
        "freight": float(frame["freight_cost"].sum()),
        "sla": float(frame["on_time_orders"].sum() / orders),
        "return_rate": float(frame["returns"].sum() / orders),
        "cancellation_rate": float(frame["cancelled_orders"].sum() / orders),
        "freight_share": float(frame["freight_cost"].sum() / revenue),
        "tickets_per_100": float(frame["support_tickets"].sum() / orders * 100),
    }


def grouped_metrics(frame: pd.DataFrame, dimension: str) -> pd.DataFrame:
    grouped = frame.groupby(dimension, as_index=False).agg(
        orders=("orders", "sum"), revenue=("revenue", "sum"),
        freight=("freight_cost", "sum"), on_time=("on_time_orders", "sum"),
        returns=("returns", "sum"), cancelled=("cancelled_orders", "sum"),
        tickets=("support_tickets", "sum"), delivery_days=("avg_delivery_days", "mean"),
    )
    grouped["sla"] = grouped["on_time"] / grouped["orders"]
    grouped["return_rate"] = grouped["returns"] / grouped["orders"]
    grouped["cancellation_rate"] = grouped["cancelled"] / grouped["orders"]
    grouped["freight_share"] = grouped["freight"] / grouped["revenue"]
    grouped["tickets_per_100"] = grouped["tickets"] / grouped["orders"] * 100
    grouped["risk_score"] = (
        ((TARGETS["sla"] - grouped["sla"]).clip(lower=0) / TARGETS["sla"] * 35)
        + ((grouped["return_rate"] - TARGETS["return_rate"]).clip(lower=0) / TARGETS["return_rate"] * 20)
        + ((grouped["cancellation_rate"] - TARGETS["cancellation_rate"]).clip(lower=0) / TARGETS["cancellation_rate"] * 20)
        + ((grouped["freight_share"] - TARGETS["freight_share"]).clip(lower=0) / TARGETS["freight_share"] * 15)
        + ((grouped["tickets_per_100"] - TARGETS["tickets_per_100"]).clip(lower=0) / TARGETS["tickets_per_100"] * 10)
    ).clip(upper=100)
    return grouped.sort_values("risk_score", ascending=False)


def status(value: float, target: float, higher_is_better: bool = False) -> str:
    ok = value >= target if higher_is_better else value <= target
    return "Dentro da meta" if ok else "Atenção"


def risk_level(score: float) -> str:
    if score >= 50:
        return "Crítico"
    if score >= 25:
        return "Alto"
    if score >= 10:
        return "Moderado"
    return "Controlado"


def action_plan(carriers: pd.DataFrame, channels: pd.DataFrame, states: pd.DataFrame) -> list[dict[str, str]]:
    actions: list[dict[str, str]] = []
    worst_carrier = carriers.iloc[0]
    worst_channel = channels.iloc[0]
    worst_state = states.iloc[0]

    if worst_carrier["sla"] < TARGETS["sla"]:
        actions.append({
            "priority": "P1", "owner": "Logística",
            "action": f"Abrir plano de recuperação de SLA com {worst_carrier['carrier']}.",
            "evidence": f"SLA {percent(worst_carrier['sla'])}, prazo médio {decimal(worst_carrier['delivery_days'])} dias.",
        })
    if worst_channel["cancellation_rate"] > TARGETS["cancellation_rate"]:
        actions.append({
            "priority": "P1", "owner": "Operações Digitais",
            "action": f"Mapear causas de cancelamento no canal {worst_channel['channel']}.",
            "evidence": f"Cancelamentos em {percent(worst_channel['cancellation_rate'])}; meta máxima {percent(TARGETS['cancellation_rate'])}.",
        })
    if worst_state["tickets_per_100"] > TARGETS["tickets_per_100"]:
        actions.append({
            "priority": "P2", "owner": "CX / Atendimento",
            "action": f"Analisar motivos de contato e jornada pós-venda em {worst_state['state']}.",
            "evidence": f"{decimal(worst_state['tickets_per_100'])} chamados por 100 pedidos.",
        })
    if worst_carrier["return_rate"] > TARGETS["return_rate"]:
        actions.append({
            "priority": "P2", "owner": "Logística Reversa",
            "action": f"Cruzar devoluções de {worst_carrier['carrier']} com motivo, produto e região.",
            "evidence": f"Taxa de devolução {percent(worst_carrier['return_rate'])}.",
        })
    if not actions:
        actions.append({
            "priority": "P3", "owner": "BI",
            "action": "Manter acompanhamento semanal e revisar metas trimestralmente.",
            "evidence": "Nenhum indicador agregado ultrapassou os limites definidos.",
        })
    return actions


def horizontal_bars(table: pd.DataFrame, label: str, value: str, target: float) -> str:
    ordered = table.sort_values(value, ascending=False)
    width, row_height = 700, 54
    parts: list[str] = []
    maximum = max(float(ordered[value].max()), target) * 1.12
    for index, row in enumerate(ordered.itertuples()):
        y = 18 + index * row_height
        current = float(getattr(row, value))
        bar_width = max(3, int(current / maximum * 430))
        color = "#b83a3a" if current > target else "#1f7a4d"
        name = html.escape(str(getattr(row, label)))
        parts.append(
            f'<text x="0" y="{y + 17}" class="chart-label">{name}</text>'
            f'<rect x="170" y="{y}" width="{bar_width}" height="25" rx="5" fill="{color}" />'
            f'<text x="{180 + bar_width}" y="{y + 18}" class="chart-value">{percent(current)}</text>'
        )
    height = 30 + len(ordered) * row_height
    return f'<svg viewBox="0 0 {width} {height}" role="img">{"".join(parts)}</svg>'


def daily_trend(frame: pd.DataFrame) -> str:
    daily = frame.groupby("date", as_index=False).agg(orders=("orders", "sum"), on_time=("on_time_orders", "sum"))
    daily["sla"] = daily["on_time"] / daily["orders"]
    width, height, left, top = 720, 230, 55, 20
    chart_w, chart_h = 625, 155
    low, high = 0.65, 1.0
    points = []
    circles = []
    for index, row in enumerate(daily.itertuples()):
        x = left + (index / max(1, len(daily) - 1)) * chart_w
        y = top + (high - row.sla) / (high - low) * chart_h
        points.append(f"{x:.1f},{y:.1f}")
        circles.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="#334155"/><text x="{x:.1f}" y="205" text-anchor="middle" class="axis">{row.date:%d/%m}</text>')
    target_y = top + (high - TARGETS["sla"]) / (high - low) * chart_h
    return (
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Evolução diária do SLA">'
        f'<line x1="{left}" y1="{target_y:.1f}" x2="{left + chart_w}" y2="{target_y:.1f}" stroke="#c58b18" stroke-dasharray="7 5"/>'
        f'<text x="{left + chart_w - 5}" y="{target_y - 7:.1f}" text-anchor="end" class="axis">Meta 92%</text>'
        f'<polyline points="{" ".join(points)}" fill="none" stroke="#334155" stroke-width="4"/>{"".join(circles)}</svg>'
    )


def detail_table(table: pd.DataFrame, dimension: str, title: str) -> str:
    rows = "".join(
        "<tr>"
        f"<td><strong>{html.escape(str(getattr(row, dimension)))}</strong></td>"
        f"<td>{integer(row.orders)}</td><td>{percent(row.sla)}</td>"
        f"<td>{percent(row.return_rate)}</td><td>{percent(row.cancellation_rate)}</td>"
        f"<td>{decimal(row.tickets_per_100)}</td>"
        f"<td><span class='risk {risk_level(row.risk_score).lower()}'>{risk_level(row.risk_score)}</span></td>"
        "</tr>" for row in table.itertuples()
    )
    return f"""<h3>{title}</h3><div class="table-scroll"><table><thead><tr>
    <th>Dimensão</th><th>Pedidos</th><th>SLA</th><th>Devoluções</th><th>Cancelamentos</th><th>Chamados/100</th><th>Risco</th>
    </tr></thead><tbody>{rows}</tbody></table></div>"""


def render_report(frame: pd.DataFrame, quality: dict[str, int], output: Path, logo: Path, watermark: Path) -> None:
    total = metrics(frame)
    carriers = grouped_metrics(frame, "carrier")
    channels = grouped_metrics(frame, "channel")
    states = grouped_metrics(frame, "state")
    actions = action_plan(carriers, channels, states)
    period = f"{frame['date'].min():%d/%m/%Y} a {frame['date'].max():%d/%m/%Y}"
    overall_risk = max(float(carriers.iloc[0]["risk_score"]), float(channels.iloc[0]["risk_score"]), float(states.iloc[0]["risk_score"]))
    verdict = risk_level(overall_risk)
    action_rows = "".join(
        f"<tr><td><span class='priority'>{item['priority']}</span></td><td>{html.escape(item['owner'])}</td>"
        f"<td>{html.escape(item['action'])}</td><td>{html.escape(item['evidence'])}</td></tr>" for item in actions
    )
    logo_uri, watermark_uri = image_data(logo), image_data(watermark)

    document = f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Commerce Ops Intelligence | CGO Data</title>
<style>
:root{{--ink:#24272c;--muted:#68717d;--line:#dfe3e8;--soft:#f4f6f8;--accent:#334155;--red:#b83a3a;--green:#1f7a4d;--amber:#c58b18}}
*{{box-sizing:border-box}}body{{margin:0;background:#e9edf1;color:var(--ink);font-family:Inter,Segoe UI,Arial,sans-serif}}
.report{{position:relative;overflow:hidden;max-width:1100px;margin:30px auto;background:white;padding:46px 55px 60px;box-shadow:0 12px 35px #1f29371f}}
.report::before{{content:"";position:absolute;inset:20% 7% 8%;background:url('{watermark_uri}') center/75% auto no-repeat;opacity:.028;pointer-events:none}}
.content{{position:relative;z-index:1}}header{{display:flex;align-items:center;justify-content:space-between;border-bottom:3px solid var(--ink);padding-bottom:18px}}
.logo{{width:185px;height:82px;object-fit:cover;object-position:center}}h1{{margin:0;font-size:29px}}.subtitle,.muted{{color:var(--muted)}}.period{{text-align:right;font-size:14px}}
.case-label{{display:inline-block;margin-top:8px;padding:5px 9px;background:#e8edf3;border-radius:4px;font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase}}
h2{{margin:34px 0 15px;font-size:21px}}h3{{margin:24px 0 10px;font-size:16px}}.executive{{display:grid;grid-template-columns:1.4fr .6fr;gap:16px}}
.narrative,.verdict{{border:1px solid var(--line);border-radius:10px;padding:20px;background:var(--soft)}}.verdict strong{{display:block;font-size:29px;margin-top:8px}}
.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}}.card{{background:var(--soft);border:1px solid var(--line);border-radius:9px;padding:16px}}
.card span{{display:block;color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.05em}}.card strong{{display:block;margin-top:6px;font-size:21px}}
.meta{{font-size:11px;margin-top:6px;color:var(--muted)}}.attention{{color:var(--red)}}.ok{{color:var(--green)}}
.grid-2{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}.chart{{border:1px solid var(--line);border-radius:10px;padding:14px;background:#fff}}
svg{{width:100%}}.chart-label,.chart-value,.axis{{fill:var(--ink);font:13px Segoe UI,Arial,sans-serif}}table{{width:100%;border-collapse:collapse;font-size:13px}}
th{{background:var(--accent);color:white;text-align:left;padding:10px 8px}}td{{border-bottom:1px solid var(--line);padding:10px 8px;vertical-align:top}}.table-scroll{{overflow-x:auto}}
.risk,.priority{{display:inline-block;padding:4px 7px;border-radius:4px;font-size:11px;font-weight:700}}.crítico{{background:#f8d7da;color:#842029}}.alto{{background:#fff0d1;color:#825d00}}.moderado{{background:#e7edf5;color:#334155}}.controlado{{background:#d9efe3;color:#17603a}}.priority{{background:#334155;color:white}}
.quality{{display:flex;gap:24px;flex-wrap:wrap;background:#eef3f7;border-left:5px solid #47657e;padding:14px 18px;font-size:13px}}footer{{margin-top:38px;border-top:1px solid var(--line);padding-top:14px;color:var(--muted);font-size:12px;display:flex;justify-content:space-between}}
@media(max-width:760px){{.report{{margin:0;padding:25px 18px}}.cards,.grid-2,.executive{{grid-template-columns:1fr}}header{{align-items:flex-start;gap:16px}}.logo{{width:125px;height:60px}}}}
@media print{{body{{background:white}}.report{{margin:0;max-width:none;box-shadow:none}}}}
</style></head><body><main class="report"><div class="content">
<header><div><img class="logo" src="{logo_uri}" alt="CGO Data"><span class="case-label">Case autoral · dados sintéticos</span></div><div class="period"><strong>Commerce Ops Intelligence</strong><br>{period}<br><span class="muted">Gerado automaticamente com Python</span></div></header>
<h1>Diagnóstico de Operações de E-commerce</h1><p class="subtitle">Monitoramento de entrega, custo logístico, devoluções, cancelamentos e impacto no atendimento.</p>
<section class="executive"><div class="narrative"><strong>Leitura executiva</strong><p>A operação processou <strong>{integer(total['orders'])} pedidos</strong> e gerou <strong>{money(total['revenue'])}</strong>. O maior foco de risco está em <strong>{html.escape(str(carriers.iloc[0]['carrier']))}</strong>, enquanto <strong>{html.escape(str(channels.iloc[0]['channel']))}</strong> é o canal que mais exige atenção combinada.</p></div><div class="verdict"><span class="muted">Criticidade operacional</span><strong>{verdict}</strong><span>Maior score: {decimal(overall_risk)}/100</span></div></section>
<h2>Painel de indicadores</h2><section class="cards">
<div class="card"><span>Pedidos</span><strong>{integer(total['orders'])}</strong><div class="meta">Volume analisado</div></div>
<div class="card"><span>Receita</span><strong>{money(total['revenue'])}</strong><div class="meta">GMV do período</div></div>
<div class="card"><span>SLA</span><strong>{percent(total['sla'])}</strong><div class="meta {'ok' if total['sla'] >= TARGETS['sla'] else 'attention'}">Meta ≥ {percent(TARGETS['sla'])}</div></div>
<div class="card"><span>Frete / receita</span><strong>{percent(total['freight_share'])}</strong><div class="meta {'ok' if total['freight_share'] <= TARGETS['freight_share'] else 'attention'}">Meta ≤ {percent(TARGETS['freight_share'])}</div></div>
<div class="card"><span>Devoluções</span><strong>{percent(total['return_rate'])}</strong><div class="meta {'ok' if total['return_rate'] <= TARGETS['return_rate'] else 'attention'}">Meta ≤ {percent(TARGETS['return_rate'])}</div></div>
<div class="card"><span>Cancelamentos</span><strong>{percent(total['cancellation_rate'])}</strong><div class="meta {'ok' if total['cancellation_rate'] <= TARGETS['cancellation_rate'] else 'attention'}">Meta ≤ {percent(TARGETS['cancellation_rate'])}</div></div>
<div class="card"><span>Chamados / 100</span><strong>{decimal(total['tickets_per_100'])}</strong><div class="meta {'ok' if total['tickets_per_100'] <= TARGETS['tickets_per_100'] else 'attention'}">Meta ≤ {decimal(TARGETS['tickets_per_100'])}</div></div>
<div class="card"><span>Custo de frete</span><strong>{money(total['freight'])}</strong><div class="meta">Despesa logística</div></div></section>
<h2>Onde está o problema?</h2><section class="grid-2"><div class="chart"><h3>Devoluções por transportadora</h3>{horizontal_bars(carriers,'carrier','return_rate',TARGETS['return_rate'])}</div><div class="chart"><h3>Cancelamentos por canal</h3>{horizontal_bars(channels,'channel','cancellation_rate',TARGETS['cancellation_rate'])}</div></section>
<h2>Evolução diária</h2><section class="chart">{daily_trend(frame)}</section>
<h2>Diagnóstico multidimensional</h2>{detail_table(carriers,'carrier','Transportadoras')}{detail_table(channels,'channel','Canais')}{detail_table(states,'state','Estados')}
<h2>Plano de ação priorizado</h2><div class="table-scroll"><table><thead><tr><th>Prioridade</th><th>Responsável sugerido</th><th>Ação</th><th>Evidência</th></tr></thead><tbody>{action_rows}</tbody></table></div>
<h2>Qualidade e rastreabilidade</h2><section class="quality"><span><strong>{quality['received']}</strong> linhas recebidas</span><span><strong>{quality['valid']}</strong> linhas válidas</span><span><strong>{quality['duplicates']}</strong> duplicidades removidas</span><span><strong>{quality['columns']}</strong> colunas validadas</span></section>
<footer><span>CGO Data — Dados que orientam decisões</span><span>Projeto demonstrativo com dados 100% sintéticos</span></footer>
</div></main></body></html>"""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(document, encoding="utf-8")


def main() -> None:
    project = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Gera o diagnóstico Commerce Ops Intelligence da CGO Data.")
    parser.add_argument("input", type=Path, help="CSV operacional de entrada")
    parser.add_argument("--output", type=Path, default=project / "reports" / "commerce_ops_intelligence.html")
    args = parser.parse_args()
    frame, quality = load_data(args.input)
    render_report(frame, quality, args.output, project / "assets" / "cgo-data-light.png", project / "assets" / "cgo-data-dark.png")
    print(f"Relatório criado: {args.output.resolve()}")


if __name__ == "__main__":
    main()
