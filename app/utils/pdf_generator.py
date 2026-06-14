import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import io
import os
import base64
from datetime import datetime
from sqlalchemy import func
from collections import defaultdict

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib import colors


def generate_pdf_report(query, region, start_date, end_date, types, filename):
    """
    Generate a PDF report from crime data query.
    
    Args:
        query: SQLAlchemy query object (already filtered)
        region: Region/district filter
        start_date: Start date string
        end_date: End date string
        types: Crime types filter (comma-separated)
        filename: Output filename
    
    Returns:
        Full file path to the generated PDF
    """
    # Get all crimes from the query
    crimes = query.all()
    total_crimes = len(crimes)
    
    # Ensure reports directory exists
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    reports_dir = os.path.join(base_dir, 'reports')
    os.makedirs(reports_dir, exist_ok=True)
    
    filepath = os.path.join(reports_dir, filename)
    
    # Create PDF document
    doc = SimpleDocTemplate(
        filepath,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch
    )
    
    # Get styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#1a1a2e')
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=14,
        spaceAfter=20,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#4a4a6a')
    )
    
    section_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=16,
        spaceBefore=20,
        spaceAfter=10,
        textColor=colors.HexColor('#16213e')
    )
    
    # Build story elements
    story = []
    
    # =============================================
    # TITLE PAGE
    # =============================================
    story.append(Spacer(1, 2 * inch))
    story.append(Paragraph("Crime Data Report", title_style))
    story.append(Spacer(1, 0.5 * inch))
    
    # Subtitle with region and date range
    region_text = region if region else "All Regions"
    date_range_text = f"{start_date or 'N/A'} to {end_date or 'N/A'}"
    subtitle_text = f"Region: {region_text}<br/>Date Range: {date_range_text}"
    story.append(Paragraph(subtitle_text, subtitle_style))
    
    # Generated timestamp
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    story.append(Spacer(1, inch))
    story.append(Paragraph(f"Generated: {timestamp}", subtitle_style))
    
    # System name at bottom
    story.append(Spacer(1, 2 * inch))
    story.append(Paragraph("Crime Data Visualization and Prediction System", subtitle_style))
    
    story.append(PageBreak())
    
    # =============================================
    # SUMMARY STATISTICS
    # =============================================
    story.append(Paragraph("Summary Statistics", section_style))
    story.append(Spacer(1, 0.3 * inch))
    
    # Calculate statistics
    crime_types_count = defaultdict(int)
    monthly_count = defaultdict(int)
    
    for crime in crimes:
        if crime.type:
            crime_types_count[crime.type] += 1
        if crime.date:
            month_key = crime.date.strftime('%Y-%m')
            monthly_count[month_key] += 1
    
    # Sort crime types by count
    sorted_types = sorted(crime_types_count.items(), key=lambda x: x[1], reverse=True)
    top_3_types = sorted_types[:3]
    
    # Calculate trend
    trend_direction = "→ Stable"
    if len(monthly_count) >= 2:
        sorted_months = sorted(monthly_count.keys())
        first_month = sorted_months[0]
        last_month = sorted_months[-1]
        first_count = monthly_count[first_month]
        last_count = monthly_count[last_month]
        
        if last_count > first_count:
            trend_direction = "↑ Increasing"
        elif last_count < first_count:
            trend_direction = "↓ Decreasing"
    
    # Summary stats table
    summary_data = [
        ['Metric', 'Value'],
        ['Total Incidents', str(total_crimes)],
        ['Date Range', f"{start_date or 'N/A'} to {end_date or 'N/A'}"],
        ['Region Filter', region if region else 'All Regions'],
        ['Types Filter', types if types else 'All Types'],
        ['Top Crime Type', top_3_types[0][0] if top_3_types else 'N/A'],
        ['Total Crime Types', str(len(crime_types_count))],
        ['Trend Direction', trend_direction]
    ]
    
    summary_table = Table(summary_data, colWidths=[3 * inch, 3 * inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#16213e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f5')])
    ]))
    story.append(summary_table)
    
    story.append(PageBreak())
    
    # =============================================
    # MONTHLY TREND TABLE
    # =============================================
    story.append(Paragraph("Monthly Trend Analysis", section_style))
    story.append(Spacer(1, 0.3 * inch))
    
    # Build monthly data
    monthly_data = [['Month', 'Count', 'Top Type', 'Change']]
    prev_count = None
    
    sorted_months = sorted(monthly_count.keys())
    for month in sorted_months:
        count = monthly_count[month]
        
        # Get top type for this month
        top_type = 'N/A'
        month_start = datetime.strptime(month + '-01', '%Y-%m-%d').date()
        if month_start.month == 12:
            month_end = datetime(month_start.year + 1, 1, 1).date()
        else:
            month_end = datetime(month_start.year, month_start.month + 1, 1).date()
        
        # Count by type for this month
        month_types = defaultdict(int)
        for crime in crimes:
            if crime.date and crime.type:
                if month_start <= crime.date < month_end:
                    month_types[crime.type] += 1
        
        if month_types:
            top_type = max(month_types.items(), key=lambda x: x[1])[0]
        
        # Calculate change
        change = ''
        if prev_count is not None and prev_count > 0:
            pct_change = ((count - prev_count) / prev_count) * 100
            change = f"{'+' if pct_change >= 0 else ''}{pct_change:.1f}%"
        
        monthly_data.append([month, str(count), top_type, change])
        prev_count = count
    
    monthly_table = Table(monthly_data, colWidths=[1.5 * inch, 1 * inch, 2 * inch, 1.5 * inch])
    monthly_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#16213e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (2, 1), (2, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f5')])
    ]))
    story.append(monthly_table)
    
    story.append(PageBreak())
    
    # =============================================
    # TOP 5 HOTSPOT COORDINATES
    # =============================================
    story.append(Paragraph("Top 5 Crime Hotspot Coordinates", section_style))
    story.append(Spacer(1, 0.3 * inch))
    
    # Group by district
    district_data = defaultdict(lambda: {'count': 0, 'lat_sum': 0, 'lng_sum': 0, 'valid_count': 0})
    
    for crime in crimes:
        if crime.district:
            district_data[crime.district]['count'] += 1
            if crime.latitude is not None and crime.longitude is not None:
                district_data[crime.district]['lat_sum'] += crime.latitude
                district_data[crime.district]['lng_sum'] += crime.longitude
                district_data[crime.district]['valid_count'] += 1
    
    # Sort by count and get top 5
    sorted_districts = sorted(district_data.items(), key=lambda x: x[1]['count'], reverse=True)[:5]
    
    hotspot_data = [['Rank', 'District', 'Count', 'Avg Latitude', 'Avg Longitude']]
    for rank, (district, data) in enumerate(sorted_districts, 1):
        avg_lat = round(data['lat_sum'] / data['valid_count'], 4) if data['valid_count'] > 0 else 0
        avg_lng = round(data['lng_sum'] / data['valid_count'], 4) if data['valid_count'] > 0 else 0
        hotspot_data.append([
            str(rank),
            district,
            str(data['count']),
            str(avg_lat),
            str(avg_lng)
        ])
    
    hotspot_table = Table(hotspot_data, colWidths=[0.8 * inch, 2 * inch, 1 * inch, 1.5 * inch, 1.5 * inch])
    hotspot_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#16213e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f5')])
    ]))
    story.append(hotspot_table)
    
    story.append(PageBreak())
    
    # =============================================
    # EMBEDDED CHARTS
    # =============================================
    story.append(Paragraph("Crime Analysis Charts", section_style))
    story.append(Spacer(1, 0.3 * inch))
    
    # Chart 1: Bar chart - Crime by Type
    if sorted_types:
        fig1 = Figure(figsize=(8, 4))
        ax1 = fig1.add_subplot(111)
        
        types_labels = [t[0][:15] + '...' if len(t[0]) > 15 else t[0] for t in sorted_types[:10]]
        types_counts = [t[1] for t in sorted_types[:10]]
        
        bars = ax1.bar(types_labels, types_counts, color='#16213e')
        ax1.set_xlabel('Crime Type')
        ax1.set_ylabel('Count')
        ax1.set_title('Top 10 Crime Types')
        ax1.tick_params(axis='x', rotation=45, labelsize=8)
        
        # Add value labels on bars
        for bar, count in zip(bars, types_counts):
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                    str(count), ha='center', va='bottom', fontsize=8)
        
        fig1.tight_layout()
        
        # Save chart to bytes
        chart1_path = os.path.join(reports_dir, 'chart1_temp.png')
        fig1.savefig(chart1_path, format='png', dpi=150, bbox_inches='tight')
        plt.close(fig1)
        
        story.append(Image(chart1_path, width=6.5 * inch, height=3.25 * inch))
        story.append(Spacer(1, 0.3 * inch))
    
    # Chart 2: Line chart - Monthly Trend
    if sorted_months:
        fig2 = Figure(figsize=(8, 4))
        ax2 = fig2.add_subplot(111)
        
        months = sorted_months
        counts = [monthly_count[m] for m in months]
        
        ax2.plot(months, counts, marker='o', linestyle='-', color='#16213e', linewidth=2)
        ax2.fill_between(months, counts, alpha=0.3, color='#4a90d9')
        ax2.set_xlabel('Month')
        ax2.set_ylabel('Count')
        ax2.set_title('Monthly Crime Trend')
        ax2.tick_params(axis='x', rotation=45, labelsize=8)
        
        # Add value labels
        for i, (m, c) in enumerate(zip(months, counts)):
            ax2.annotate(str(c), (m, c), textcoords="offset points", xytext=(0, 5), ha='center', fontsize=8)
        
        fig2.tight_layout()
        
        chart2_path = os.path.join(reports_dir, 'chart2_temp.png')
        fig2.savefig(chart2_path, format='png', dpi=150, bbox_inches='tight')
        plt.close(fig2)
        
        story.append(Image(chart2_path, width=6.5 * inch, height=3.25 * inch))
    
    story.append(PageBreak())
    
    # =============================================
    # CRIME HOTSPOT MAP SNAPSHOT
    # =============================================
    story.append(Paragraph("Crime Hotspot Map", section_style))
    story.append(Spacer(1, 0.3 * inch))
    
    # Get crimes with coordinates
    crimes_with_coords = [(c.latitude, c.longitude) for c in crimes 
                          if c.latitude is not None and c.longitude is not None]
    
    if crimes_with_coords:
        fig3 = Figure(figsize=(8, 6))
        ax3 = fig3.add_subplot(111)
        
        lats = [c[0] for c in crimes_with_coords]
        lngs = [c[1] for c in crimes_with_coords]
        
        # Create scatter plot with size based on density
        ax3.scatter(lngs, lats, alpha=0.5, s=20, c='#e74c3c')
        ax3.set_xlabel('Longitude')
        ax3.set_ylabel('Latitude')
        ax3.set_title(f'Crime Locations ({len(crimes_with_coords)} incidents)')
        
        # Add grid
        ax3.grid(True, alpha=0.3)
        
        fig3.tight_layout()
        
        chart3_path = os.path.join(reports_dir, 'chart3_temp.png')
        fig3.savefig(chart3_path, format='png', dpi=150, bbox_inches='tight')
        plt.close(fig3)
        
        story.append(Image(chart3_path, width=6 * inch, height=4.5 * inch))
    else:
        story.append(Paragraph("No coordinate data available for map visualization.", styles['Normal']))
    
    # =============================================
    # BUILD PDF
    # =============================================
    doc.build(story)
    
    # Clean up temporary chart files
    for chart_file in ['chart1_temp.png', 'chart2_temp.png', 'chart3_temp.png']:
        chart_path = os.path.join(reports_dir, chart_file)
        if os.path.exists(chart_path):
            try:
                os.remove(chart_path)
            except:
                pass
    
    return filepath