"""
Export utilities for TraceTrack application.
Provides CSV and PDF export functionality for reports and analytics.
"""
import csv
import io
from datetime import datetime
from flask import make_response
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from models import Bag, BagType, Bill, Scan, Location
from app import db


def export_bags_csv():
    """Export parent and child bags data to CSV format."""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write headers
    writer.writerow([
        'Type', 'QR ID', 'Name', 'Child Count', 'Parent QR ID', 
        'Bill ID', 'Created At', 'Status'
    ])
    
    # Export all bags
    bags = Bag.query.all()
    for bag in bags:
        bag_type = 'Parent' if bag.type == BagType.PARENT.value else 'Child'
        parent_qr_id = ''
        child_count = ''
        
        # For child bags, find parent relationship
        if bag.type == BagType.CHILD.value:
            from models import Link
            link = Link.query.filter_by(child_qr_id=bag.qr_id).first()
            if link:
                parent_qr_id = link.parent_qr_id
        
        # For parent bags, count children
        if bag.type == BagType.PARENT.value:
            from models import Link
            child_count = Link.query.filter_by(parent_qr_id=bag.qr_id).count()
        
        writer.writerow([
            bag_type,
            bag.qr_id,
            bag.name or f'{bag_type} Bag',
            child_count,
            parent_qr_id,
            getattr(bag, 'bill_id', '') or '',
            bag.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'Linked' if parent_qr_id else 'Active'
        ])
    
    output.seek(0)
    return output.getvalue()


def export_scans_csv():
    """Export scan history to CSV format."""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write headers
    writer.writerow([
        'Scan ID', 'QR ID', 'Bag Type', 'Location', 'User ID', 
        'Timestamp', 'Notes'
    ])
    
    # Export scans
    scans = Scan.query.order_by(Scan.timestamp.desc()).all()
    for scan in scans:
        bag_type = 'Parent' if scan.parent_bag else 'Child'
        location_name = scan.location.name if scan.location else 'Unknown'
        
        writer.writerow([
            scan.id,
            scan.qr_id,
            bag_type,
            location_name,
            scan.user_id or 'System',
            scan.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            scan.notes or ''
        ])
    
    output.seek(0)
    return output.getvalue()


def export_bills_csv():
    """Export bills data to CSV format."""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write headers
    writer.writerow([
        'Bill ID', 'Status', 'Parent Bags Count', 'Linked Bags', 
        'Progress %', 'Created At'
    ])
    
    # Export bills
    bills = Bill.query.all()
    for bill in bills:
        linked_count = len([bag for bag in bill.parent_bags if bag.child_count > 0])
        total_count = len(bill.parent_bags)
        progress = (linked_count / total_count * 100) if total_count > 0 else 0
        
        writer.writerow([
            bill.id,
            bill.status,
            total_count,
            linked_count,
            f"{progress:.1f}%",
            bill.created_at.strftime('%Y-%m-%d %H:%M:%S')
        ])
    
    output.seek(0)
    return output.getvalue()


def create_pdf_report():
    """Create a comprehensive PDF report."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        textColor=colors.HexColor('#2d5a3d')
    )
    story.append(Paragraph("STAR Agriseeds TraceTrack Report", title_style))
    story.append(Spacer(1, 20))
    
    # Report metadata
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Summary statistics
    parent_count = Bag.query.filter_by(type=BagType.PARENT.value).count()
    child_count = Bag.query.filter_by(type=BagType.CHILD.value).count()
    bill_count = Bill.query.count()
    scan_count = Scan.query.count()
    
    summary_data = [
        ['Metric', 'Count'],
        ['Parent Bags (Seed Batches)', str(parent_count)],
        ['Child Bags (Products)', str(child_count)],
        ['Active Bills', str(bill_count)],
        ['Total Scans', str(scan_count)]
    ]
    
    summary_table = Table(summary_data)
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2d5a3d')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(Paragraph("Summary Statistics", styles['Heading2']))
    story.append(summary_table)
    story.append(Spacer(1, 30))
    
    # Recent scans table
    recent_scans = Scan.query.order_by(Scan.timestamp.desc()).limit(10).all()
    if recent_scans:
        story.append(Paragraph("Recent Scan Activity", styles['Heading2']))
        
        scan_data = [['QR ID', 'Type', 'Location', 'Timestamp']]
        for scan in recent_scans:
            bag_type = 'Parent' if scan.parent_bag else 'Child'
            location_name = scan.location.name if scan.location else 'Unknown'
            scan_data.append([
                scan.qr_id,
                bag_type,
                location_name,
                scan.timestamp.strftime('%Y-%m-%d %H:%M')
            ])
        
        scan_table = Table(scan_data)
        scan_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a7c59')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(scan_table)
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def create_csv_response(data, filename):
    """Create a Flask response for CSV download."""
    response = make_response(data)
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response


def create_pdf_response(data, filename):
    """Create a Flask response for PDF download."""
    response = make_response(data)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response