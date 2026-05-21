"""
Seed script for initial applicant positions.

Creates the standard job positions that applicants can apply for.

Run with: python seed_positions.py
"""

import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ats_app import create_app, db
from models import Position, Employee


# Default positions to seed
DEFAULT_POSITIONS = [
    {
        'title': 'Software Engineer',
        'description': 'Full-stack software development, coding, and technical implementation'
    },
    {
        'title': 'HR Manager',
        'description': 'Human resources management, recruitment, and employee relations'
    },
    {
        'title': 'Data Analyst',
        'description': 'Data analysis, reporting, and insights generation'
    },
    {
        'title': 'Project Manager',
        'description': 'Project planning, coordination, and team management'
    },
    {
        'title': 'Marketing Specialist',
        'description': 'Marketing campaigns, digital marketing, and brand management'
    },
    {
        'title': 'Sales Representative',
        'description': 'Sales, client relations, and business development'
    },
    {
        'title': 'Customer Support',
        'description': 'Customer service, support, and issue resolution'
    },
    {
        'title': 'DevOps Engineer',
        'description': 'Infrastructure, deployment, and system administration'
    },
    {
        'title': 'UI/UX Designer',
        'description': 'User interface and user experience design'
    },
    {
        'title': 'Business Analyst',
        'description': 'Business analysis, requirements gathering, and process improvement'
    },
]


def seed_positions():
    """Seed initial job positions."""
    
    app = create_app(enable_applicant=True, enable_employee=True, root_redirect='applicant_home')
    
    with app.app_context():
        print("\n" + "="*60)
        print("ATS Position Management - Seeding")
        print("="*60)
        
        # Create all tables
        print("\n[1/2] Creating database tables...")
        db.create_all()
        print("✓ Tables created successfully")
        
        # Seed positions
        print("\n[2/2] Seeding job positions...")
        
        superadmin = Employee.query.filter_by(username='SUPERADMIN').first()
        created_by_id = superadmin.id if superadmin else None
        
        created_count = 0
        skipped_count = 0
        
        for pos_data in DEFAULT_POSITIONS:
            existing = Position.query.filter_by(title=pos_data['title']).first()
            
            if existing:
                print(f"  ⚠ '{pos_data['title']}' already exists, skipping")
                skipped_count += 1
            else:
                position = Position(
                    title=pos_data['title'],
                    description=pos_data.get('description'),
                    is_active=True,
                    created_by_id=created_by_id
                )
                db.session.add(position)
                created_count += 1
        
        db.session.commit()
        
        print(f"\n✓ Positions seeded:")
        print(f"  - {created_count} new positions created")
        print(f"  - {skipped_count} positions already existed")
        print(f"  - Total positions: {Position.query.count()}")
        
        # List all positions
        print("\n📍 Available Positions:")
        all_positions = Position.query.filter_by(is_active=True).all()
        for i, pos in enumerate(all_positions, 1):
            print(f"  {i}. {pos.title}")
            if pos.description:
                print(f"     {pos.description}")
        
        print("\n" + "="*60)
        print("✓ Position seeding completed successfully!")
        print("="*60)
        print("\nNEXT STEPS:")
        print("1. Positions are now available in the applicant registration form")
        print("2. SUPERADMIN can add/edit/delete positions via admin panel")
        print("3. Navigate to: http://localhost:5000/admin-panel.html")
        print("4. Go to 'Positions' tab to manage positions")
        print("\n")
        
        return True


if __name__ == '__main__':
    try:
        success = seed_positions()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Error during seeding: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
