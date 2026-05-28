from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from xml.sax.saxutils import escape


OUT = Path("ARTS Deployment Procedure.pdf")


def p(text, style):
    return Paragraph(text.replace("&", "&amp;"), style)


def bullets(items, style):
    return ListFlowable(
        [ListItem(p(item, style), leftIndent=12) for item in items],
        bulletType="bullet",
        start="circle",
        leftIndent=18,
        bulletFontSize=7,
    )


def numbers(items, style):
    return ListFlowable(
        [ListItem(p(item, style), leftIndent=12) for item in items],
        bulletType="1",
        leftIndent=18,
    )


def code(text, style):
    lines = []
    for line in text.splitlines():
        if not line:
            lines.append("")
            continue
        lines.append(escape(line).replace(" ", "&nbsp;"))
    return Paragraph("<br/>".join(lines), style)


def simple_table(rows, widths):
    table = Table(rows, colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EEF5")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0B2545")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#B8C4D4")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#666666"))
    canvas.drawCentredString(letter[0] / 2, 0.45 * inch, f"ARTS Deployment Procedure - Page {doc.page}")
    canvas.restoreState()


def build():
    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=letter,
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.7 * inch,
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle("Title", parent=styles["Title"], alignment=TA_CENTER, fontName="Helvetica-Bold", fontSize=22, leading=26, textColor=colors.HexColor("#0B2545"), spaceAfter=4)
    subtitle = ParagraphStyle("Subtitle", parent=styles["Normal"], alignment=TA_CENTER, fontSize=9, leading=12, textColor=colors.HexColor("#555555"), spaceAfter=14)
    h1 = ParagraphStyle("H1", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=13, leading=16, textColor=colors.HexColor("#2E74B5"), spaceBefore=10, spaceAfter=5)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=11, leading=13, textColor=colors.HexColor("#1F4D78"), spaceBefore=8, spaceAfter=4)
    body = ParagraphStyle("Body", parent=styles["BodyText"], fontName="Helvetica", fontSize=9.2, leading=11.5, spaceAfter=5)
    small = ParagraphStyle("Small", parent=body, fontSize=8.2, leading=10)
    mono = ParagraphStyle("Mono", parent=styles["Code"], fontName="Courier", fontSize=6.8, leading=8.4, leftIndent=8, rightIndent=8, backColor=colors.HexColor("#F4F6F9"), borderColor=colors.HexColor("#D8DEE8"), borderWidth=0.25, borderPadding=5, spaceBefore=2, spaceAfter=6, wordWrap="CJK")

    story = [
        Paragraph("ARTS Deployment Procedure", title),
        Paragraph("Ubuntu server, Hostinger domain, Cloudflare, Nginx reverse proxy, Flask/Gunicorn, PostgreSQL, and Synology backup/storage", subtitle),
        Paragraph("1. Target Architecture", h1),
        bullets([
            "Users access https://yourdomain.com through Cloudflare.",
            "Cloudflare proxies traffic to your public static IP and provides DNS, SSL edge protection, DDoS protection, and security rules.",
            "Your router forwards only TCP 80 and 443 to the Ubuntu server.",
            "Nginx receives public traffic and reverse-proxies requests to Gunicorn on 127.0.0.1:5000.",
            "Gunicorn runs the Flask ARTS application from app:app.",
            "PostgreSQL stores application data. The current system stores applicant PDFs and profile images inside PostgreSQL binary columns.",
            "Synology receives scheduled database backups. Optional future app changes can store uploaded PDFs directly on a Synology-mounted share.",
        ], body),
        Paragraph("2. Things To Buy Or Prepare", h1),
        simple_table([
            ["Item", "Purpose"],
            ["Domain from Hostinger", "Public name for the ARTS system."],
            ["Static public IPv4 from ISP", "Required for reliable self-hosting from your custom Ubuntu PC."],
            ["Cloudflare Free or Pro", "DNS, CDN, DDoS protection, SSL, WAF/rate controls. Start Free; consider Pro for heavier traffic."],
            ["UPS battery backup", "Keeps Ubuntu server, router, modem, and Synology online during short power loss."],
            ["Synology NAS storage", "Local backup target and optional uploaded-file storage."],
            ["Offsite backup storage", "Recommended second backup copy: Backblaze B2, AWS S3, Wasabi, or Synology C2."],
            ["Optional firewall/router", "pfSense, OPNsense, MikroTik, or UniFi for stronger network control."],
        ], [1.65 * inch, 5.25 * inch]),
        Paragraph("3. Ubuntu Server Setup", h1),
        numbers([
            "Log in to the Ubuntu server with SSH.",
            "Update the server and install Python, PostgreSQL, Nginx, UFW, Fail2ban, Git, and backup tools.",
            "Create a dedicated Linux user named ats.",
            "Place the project in /home/ats/app.",
            "Create a production .env file with SECRET_KEY and DATABASE_URL.",
            "Create a Python virtual environment and install requirements plus gunicorn.",
            "Test Gunicorn locally before exposing the site.",
        ], body),
        code("sudo apt update && sudo apt upgrade -y\nsudo apt install -y python3 python3-venv python3-pip \\\n    postgresql postgresql-contrib nginx ufw fail2ban \\\n    git curl unzip rsync postgresql-client\nsudo adduser ats\nsudo usermod -aG sudo ats\nsu - ats\nmkdir -p /home/ats/app\ncd /home/ats/app\npython3 -m venv .venv\nsource .venv/bin/activate\npip install --upgrade pip\npip install -r requirements.txt\npip install gunicorn", mono),
        Paragraph("4. PostgreSQL Setup", h1),
        bullets([
            "Create the ats database and a non-admin user named ats_user.",
            "Use a long random password.",
            "Do not expose PostgreSQL port 5432 to the internet.",
        ], body),
        code("sudo -u postgres psql\nCREATE DATABASE ats;\nCREATE USER ats_user WITH ENCRYPTED PASSWORD 'REPLACE_WITH_LONG_RANDOM_DB_PASSWORD';\nGRANT ALL PRIVILEGES ON DATABASE ats TO ats_user;\n\\q\nsudo -u postgres psql -d ats\nGRANT ALL ON SCHEMA public TO ats_user;\nALTER SCHEMA public OWNER TO ats_user;\n\\q", mono),
        Paragraph("5. Production Environment File", h1),
        code("cd /home/ats/app\nnano .env\n\nSECRET_KEY=REPLACE_WITH_LONG_RANDOM_SECRET_KEY\nDATABASE_URL=postgresql://ats_user:REPLACE_WITH_LONG_RANDOM_DB_PASSWORD@localhost:5432/ats\nFLASK_ENV=production", mono),
        Paragraph("6. Gunicorn Systemd Service", h1),
        code("sudo nano /etc/systemd/system/ats.service\n\n[Unit]\nDescription=Applicant Tracking System Flask App\nAfter=network.target postgresql.service\n\n[Service]\nUser=ats\nGroup=www-data\nWorkingDirectory=/home/ats/app\nEnvironmentFile=/home/ats/app/.env\nExecStart=/home/ats/app/.venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 app:app\nRestart=always\nRestartSec=5\n\n[Install]\nWantedBy=multi-user.target\n\nsudo systemctl daemon-reload\nsudo systemctl enable ats\nsudo systemctl start ats\nsudo systemctl status ats", mono),
        Paragraph("7. Nginx Reverse Proxy", h1),
        Paragraph("<b>Reverse proxy meaning:</b> Nginx is the public front door on ports 80/443. It forwards requests internally to Flask/Gunicorn on 127.0.0.1:5000. This keeps Flask off the public internet and lets Nginx handle HTTPS, static files, rate limiting, and buffering.", body),
        code("sudo nano /etc/nginx/sites-available/ats\n\nserver {\n    listen 80;\n    server_name yourdomain.com www.yourdomain.com;\n    client_max_body_size 5M;\n\n    add_header X-Frame-Options \"SAMEORIGIN\" always;\n    add_header X-Content-Type-Options \"nosniff\" always;\n    add_header Referrer-Policy \"strict-origin-when-cross-origin\" always;\n\n    location /static/ {\n        alias /home/ats/app/static/;\n        expires 7d;\n        add_header Cache-Control \"public\";\n    }\n\n    location / {\n        proxy_pass http://127.0.0.1:5000;\n        proxy_http_version 1.1;\n        proxy_set_header Host $host;\n        proxy_set_header X-Real-IP $remote_addr;\n        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n        proxy_set_header X-Forwarded-Proto $scheme;\n    }\n}\n\nsudo ln -s /etc/nginx/sites-available/ats /etc/nginx/sites-enabled/ats\nsudo nginx -t\nsudo systemctl reload nginx", mono),
        Paragraph("8. Firewall And Router", h1),
        bullets([
            "Ubuntu UFW: allow only OpenSSH, 80/tcp, and 443/tcp.",
            "Router port forwarding: forward public TCP 80 and 443 only to the Ubuntu server LAN IP.",
            "Do not forward Flask 5000, PostgreSQL 5432, Synology DSM 5000/5001, SMB 445, rsync 873, or NFS 2049.",
        ], body),
        code("sudo ufw default deny incoming\nsudo ufw default allow outgoing\nsudo ufw allow OpenSSH\nsudo ufw allow 80/tcp\nsudo ufw allow 443/tcp\nsudo ufw enable\nsudo ufw status verbose", mono),
        Paragraph("9. Hostinger Domain And Cloudflare DNS", h1),
        numbers([
            "In Hostinger hPanel, go to Domains > Get a new domain, buy the domain, enable privacy if available, and enable auto-renewal.",
            "In Cloudflare, click Add a site, enter the domain, and choose Free or Pro.",
            "In Cloudflare DNS, add an A record for @ pointing to your static public IPv4. Set proxy status to Proxied.",
            "Add a CNAME record for www pointing to your root domain. Set proxy status to Proxied.",
            "Cloudflare will show two nameservers.",
            "In Hostinger hPanel, go to Domains > Domain portfolio > Manage > DNS / Nameservers > Change Nameservers.",
            "Enter the two Cloudflare nameservers and save. Wait for propagation, usually minutes to 24 hours.",
        ], body),
        simple_table([
            ["Type", "Name", "Target", "Proxy"],
            ["A", "@", "YOUR_PUBLIC_STATIC_IP", "Proxied"],
            ["CNAME", "www", "yourdomain.com", "Proxied"],
        ], [0.8 * inch, 0.8 * inch, 3.8 * inch, 1.1 * inch]),
        Paragraph("10. HTTPS Certificate", h1),
        code("sudo apt install -y certbot python3-certbot-nginx\nsudo certbot --nginx -d yourdomain.com -d www.yourdomain.com\nsudo certbot renew --dry-run", mono),
        bullets([
            "In Cloudflare SSL/TLS, set mode to Full (strict).",
            "Enable Always Use HTTPS.",
            "Confirm https://yourdomain.com loads before announcing the system.",
        ], body),
        Paragraph("11. Synology Backup Configuration", h1),
        numbers([
            "In Synology DSM, open Control Panel > Shared Folder > Create > Create Shared Folder.",
            "Create a shared folder named ats_backups.",
            "Enable Recycle Bin. Enable encryption if your Synology supports it.",
            "Open Control Panel > User & Group > Create.",
            "Create a non-admin user named ats_backup.",
            "Give ats_backup Read/Write access only to ats_backups and No Access to other folders.",
            "Open Control Panel > File Services > rsync and enable rsync service.",
            "Open Control Panel > Application Privileges > rsync > Edit and allow ats_backup. Restrict to the Ubuntu server LAN IP if available.",
        ], body),
        code("nano /home/ats/backup_to_synology.sh\n\n#!/bin/bash\nset -e\nDATE=$(date +%F-%H%M)\nLOCAL_BACKUP_DIR=\"/var/backups/ats\"\nDB_URL=\"postgresql://ats_user:YOUR_DB_PASSWORD@localhost:5432/ats\"\nSYNOLOGY_IP=\"192.168.1.20\"\nSYNOLOGY_USER=\"ats_backup\"\nSYNOLOGY_TARGET=\"ats_backups\"\nmkdir -p \"$LOCAL_BACKUP_DIR\"\npg_dump \"$DB_URL\" | gzip > \"$LOCAL_BACKUP_DIR/ats-db-$DATE.sql.gz\"\nrsync -avz \"$LOCAL_BACKUP_DIR/\" \"$SYNOLOGY_USER@$SYNOLOGY_IP:/$SYNOLOGY_TARGET/\"\nfind \"$LOCAL_BACKUP_DIR\" -type f -name \"*.gz\" -mtime +7 -delete\n\nchmod +x /home/ats/backup_to_synology.sh\n/home/ats/backup_to_synology.sh\ncrontab -e\n0 2 * * * /home/ats/backup_to_synology.sh >> /home/ats/backup.log 2>&1", mono),
        Paragraph("12. Uploaded PDFs And Excel Files", h1),
        bullets([
            "Current behavior: applicant CV PDFs are stored in PostgreSQL as applicant.cv_data.",
            "Current behavior: employee profile images are stored in PostgreSQL as employee.profile_data.",
            "Current behavior: Excel exports are generated in memory and downloaded; they are not permanently stored by the app.",
            "Because PDFs are currently inside PostgreSQL, the Synology database backup includes the PDFs.",
            "Optional future improvement: change the app to store uploads on /mnt/ats_uploads and keep only file path, filename, content type, size, and checksum in PostgreSQL.",
        ], body),
        Paragraph("13. Optional Direct Synology Upload Storage", h1),
        numbers([
            "In DSM, create another shared folder named ats_uploads.",
            "Create a non-admin user named ats_storage.",
            "Give ats_storage Read/Write access only to ats_uploads.",
            "On Ubuntu, mount the Synology share at /mnt/ats_uploads using CIFS.",
            "Only after the mount is reliable, modify the Flask app to write PDFs/profile images to that mount instead of database binary columns.",
        ], body),
        code("sudo apt install -y cifs-utils\nsudo mkdir -p /mnt/ats_uploads\nsudo nano /etc/ats-synology-credentials\n\nusername=ats_storage\npassword=YOUR_STRONG_SYNOLOGY_PASSWORD\n\nsudo chmod 600 /etc/ats-synology-credentials\nsudo nano /etc/fstab\n\n//192.168.1.20/ats_uploads /mnt/ats_uploads cifs \\\n    credentials=/etc/ats-synology-credentials,uid=ats,gid=www-data,\\\n    file_mode=0640,dir_mode=0750,iocharset=utf8,nofail,_netdev 0 0\nsudo mount -a", mono),
        Paragraph("14. Security Checklist", h1),
        bullets([
            "Use Cloudflare proxy for @ and www DNS records.",
            "Expose only ports 80 and 443 to the internet.",
            "Keep Synology LAN-only; never port-forward DSM, SMB, rsync, or NFS.",
            "Disable SSH password login after SSH key login is confirmed.",
            "Use Fail2ban.",
            "Use strong unique passwords for PostgreSQL, Synology users, Ubuntu users, and Cloudflare/Hostinger.",
            "Enable 2FA on Hostinger, Cloudflare, Synology, and admin email accounts.",
            "Back up PostgreSQL nightly to Synology and keep at least one offsite backup copy.",
            "Test restores regularly, not only backups.",
            "Review application logs and Nginx logs weekly during launch.",
        ], body),
        Paragraph("15. Deployment Update Procedure", h1),
        code("cd /home/ats/app\ngit pull\nsource .venv/bin/activate\npip install -r requirements.txt\nsudo systemctl restart ats\nsudo systemctl status ats\njournalctl -u ats -n 100 --no-pager", mono),
        Paragraph("16. Go-Live Verification", h1),
        bullets([
            "https://yourdomain.com loads successfully.",
            "Applicant registration form works.",
            "PDF CV upload works.",
            "Employee login works.",
            "Dashboard loads and can download CVs.",
            "Excel export works.",
            "Cloudflare DNS records are proxied.",
            "External scan shows only ports 80 and 443 open.",
            "PostgreSQL 5432, Flask 5000, and Synology ports are closed externally.",
            "Synology backup script has produced a recent .sql.gz backup.",
        ], body),
        Paragraph("17. Source References", h1),
        bullets([
            "Hostinger DNS records: https://support.hostinger.com/en/articles/1583249-how-to-manage-dns-records-at-hostinger",
            "Hostinger A records: https://support.hostinger.com/en/articles/4468886-how-to-add-and-remove-a-records-in-hpanel/",
            "Docker on Ubuntu: https://docs.docker.com/engine/install/ubuntu/",
            "Gunicorn deployment: https://docs.gunicorn.org/en/19.9.0/deploy.html",
            "Cloudflare Free plan: https://www.cloudflare.com/plans/free/",
            "Cloudflare Universal SSL: https://developers.cloudflare.com/ssl/edge-certificates/universal-ssl/",
            "Synology shared folders: https://kb.synology.com/en-af/PAS/help/PAS/AdminCenter/file_share_create",
            "Synology rsync: https://kb.synology.com/en-us/DSM/help/DSM/AdminCenter/file_rsync?version=7",
        ], small),
    ]

    doc.build(story, onFirstPage=footer, onLaterPages=footer)


if __name__ == "__main__":
    build()
