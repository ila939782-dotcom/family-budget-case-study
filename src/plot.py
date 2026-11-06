"""Plot the synthetic activation funnel, preserving the eligible denominator."""
import csv
import json
from pathlib import Path
from reportlab.graphics.shapes import Drawing, String
from reportlab.graphics.charts.barcharts import HorizontalBarChart
from reportlab.graphics import renderPDF
from reportlab.lib import colors
import pypdfium2 as pdfium

ROOT=Path(__file__).resolve().parents[1]


def plot():
    with (ROOT/'reports/funnel.csv').open() as f:
        rows=list(csv.DictReader(f))
    s=json.loads((ROOT/'reports/summary.json').read_text())
    d=Drawing(1000,380)
    navy=colors.HexColor('#172b4d')
    d.add(String(28,345,'FAMILY BUDGET  /  ACTIVATION MEASUREMENT',fontName='Helvetica-Bold',fontSize=20,fillColor=navy))
    d.add(String(28,320,'Synthetic event sample  /  300 users  /  7-day activation window',fontSize=12,fillColor=colors.HexColor('#526275')))
    chart=HorizontalBarChart();chart.x=210;chart.y=80;chart.width=480;chart.height=200
    chart.data=[[int(r['users']) for r in reversed(rows)]]
    chart.categoryAxis.categoryNames=['Report viewed','Limit set','Family created','Exposed (mature)']
    chart.valueAxis.valueMin=0;chart.valueAxis.valueMax=int(rows[0]['users'])*1.15
    chart.bars[0].fillColor=colors.HexColor('#2563eb');chart.bars[0].strokeColor=colors.HexColor('#2563eb');chart.categoryAxis.labels.fontName='Helvetica';chart.valueAxis.labels.fontName='Helvetica';chart.barLabels.fontName='Helvetica';chart.barLabelFormat='%d';chart.barLabels.fontSize=12
    chart.valueAxis.visibleGrid=True;chart.valueAxis.gridStrokeColor=colors.HexColor('#e5e7eb')
    d.add(chart)
    def pct(v):return f'{v:.1%}' if v is not None else 'n.a.'
    d.add(String(750,240,pct(s['activation_rate']),fontName='Helvetica-Bold',fontSize=32,fillColor=navy))
    d.add(String(750,215,'7-day activation',fontSize=12,fillColor=navy))
    d.add(String(750,155,pct(s['retention_d14']),fontName='Helvetica-Bold',fontSize=32,fillColor=navy))
    d.add(String(750,130,f"D14: {s['retained_d14_users']} / {s['d14_eligible_activated_users']} eligible",fontSize=12,fillColor=navy))
    d.add(String(28,30,f"{s['excluded_immature_funnel_users']} immature users excluded from activation denominator. Cutoff: {s['as_of_exclusive_utc']} UTC (exclusive).",fontSize=11,fillColor=navy))
    pdf=pdfium.PdfDocument(renderPDF.drawToString(d));pdf[0].render(scale=1.6).to_pil().save(ROOT/'reports/funnel.png');pdf.close()


if __name__=='__main__':
    plot()
