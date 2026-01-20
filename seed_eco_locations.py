"""
Seed script to populate eco-locations database with sample data
Run this script to add initial eco-locations for testing
"""

from database import eco_locations_collection
from datetime import datetime, timedelta

def seed_eco_locations():
    """Add sample eco-locations to the database"""
    
    # Clear existing data (optional - comment out if you want to keep existing data)
    # eco_locations_collection.delete_many({})
    
    # Check if data already exists
    if eco_locations_collection.count_documents({}) > 0:
        print(f"Database already has {eco_locations_collection.count_documents({})} locations.")
        response = input("Do you want to clear and reseed? (yes/no): ")
        if response.lower() == 'yes':
            eco_locations_collection.delete_many({})
            print("Cleared existing data.")
        else:
            print("Keeping existing data. Exiting.")
            return
    
    timestamp = int(datetime.now().timestamp())
    
    # Sample locations for Kathmandu
    kathmandu_locations = [
        {
            "name": "Bagmati River Plantation Drive",
            "category": "plantation_event",
            "description": "Join us for a massive tree planting event along the Bagmati River. We aim to plant 500 trees to restore the riverbank ecosystem.",
            "city": "Kathmandu",
            "location": {"type": "Point", "coordinates": [85.3240, 27.7172]},
            "latitude": 27.7172,
            "longitude": 85.3240,
            "address": "Bagmati Riverside, Thapathali, Kathmandu",
            "contact": {
                "phone": "+977-9841234567",
                "email": "info@greenngo.org",
                "website": "https://greenngo.org"
            },
            "eventDate": (datetime.now() + timedelta(days=15)).isoformat(),
            "startTime": "07:00 AM",
            "endTime": "12:00 PM",
            "organizer": "Green Nepal NGO",
            "targetTrees": 500,
            "volunteersNeeded": 100,
            "volunteersRegistered": 45,
            "estimatedCO2Offset": "2.5 tons/year",
            "status": "upcoming",
            "images": [],
            "verified": True,
            "addedBy": "admin",
            "createdAt": timestamp,
            "updatedAt": timestamp
        },
        {
            "name": "Swayambhu Recycling Center",
            "category": "recycling_center",
            "description": "Full-service recycling facility accepting paper, plastic, glass, metal, and electronics. Free drop-off for residents.",
            "city": "Kathmandu",
            "location": {"type": "Point", "coordinates": [85.2900, 27.7150]},
            "latitude": 27.7150,
            "longitude": 85.2900,
            "address": "Swayambhu Circle, Kathmandu",
            "contact": {
                "phone": "+977-1-4271234",
                "email": "info@swayambhurecycle.com"
            },
            "hours": {
                "monday": "9:00 AM - 6:00 PM",
                "tuesday": "9:00 AM - 6:00 PM",
                "wednesday": "9:00 AM - 6:00 PM",
                "thursday": "9:00 AM - 6:00 PM",
                "friday": "9:00 AM - 6:00 PM",
                "saturday": "9:00 AM - 4:00 PM",
                "sunday": "Closed"
            },
            "amenities": ["Free parking", "Accepts electronics", "Cash for metal"],
            "images": [],
            "verified": True,
            "addedBy": "admin",
            "createdAt": timestamp,
            "updatedAt": timestamp
        },
        {
            "name": "Thamel Eco Store",
            "category": "eco_store",
            "description": "Zero-waste store offering sustainable products, organic foods, reusable containers, and eco-friendly alternatives.",
            "city": "Kathmandu",
            "location": {"type": "Point", "coordinates": [85.3100, 27.7150]},
            "latitude": 27.7150,
            "longitude": 85.3100,
            "address": "Thamel Marg, Kathmandu",
            "contact": {
                "phone": "+977-1-4700123",
                "email": "hello@thamelecostore.com",
                "website": "https://thamelecostore.com"
            },
            "hours": {
                "monday": "10:00 AM - 8:00 PM",
                "tuesday": "10:00 AM - 8:00 PM",
                "wednesday": "10:00 AM - 8:00 PM",
                "thursday": "10:00 AM - 8:00 PM",
                "friday": "10:00 AM - 8:00 PM",
                "saturday": "10:00 AM - 8:00 PM",
                "sunday": "10:00 AM - 6:00 PM"
            },
            "amenities": ["Bulk buying", "Refill station", "Composting supplies"],
            "images": [],
            "verified": True,
            "addedBy": "admin",
            "createdAt": timestamp,
            "updatedAt": timestamp
        },
        {
            "name": "Climate Action Network Nepal",
            "category": "ngo_office",
            "description": "Leading environmental NGO working on climate change mitigation, renewable energy advocacy, and community awareness programs.",
            "city": "Kathmandu",
            "location": {"type": "Point", "coordinates": [85.3200, 27.7100]},
            "latitude": 27.7100,
            "longitude": 85.3200,
            "address": "Lazimpat, Kathmandu",
            "contact": {
                "phone": "+977-1-4443210",
                "email": "info@cannepal.org",
                "website": "https://cannepal.org"
            },
            "hours": {
                "monday": "10:00 AM - 5:00 PM",
                "tuesday": "10:00 AM - 5:00 PM",
                "wednesday": "10:00 AM - 5:00 PM",
                "thursday": "10:00 AM - 5:00 PM",
                "friday": "10:00 AM - 5:00 PM"
            },
            "amenities": ["Volunteer programs", "Educational workshops", "Research library"],
            "images": [],
            "verified": True,
            "addedBy": "admin",
            "createdAt": timestamp,
            "updatedAt": timestamp
        },
        {
            "name": "Balaju Community Garden",
            "category": "community_garden",
            "description": "Urban farming space with organic vegetable plots, composting area, and community workshops on sustainable agriculture.",
            "city": "Kathmandu",
            "location": {"type": "Point", "coordinates": [85.3000, 27.7300]},
            "latitude": 27.7300,
            "longitude": 85.3000,
            "address": "Balaju, Kathmandu",
            "contact": {
                "phone": "+977-9851234567",
                "email": "balajugarden@gmail.com"
            },
            "hours": {
                "monday": "6:00 AM - 6:00 PM",
                "tuesday": "6:00 AM - 6:00 PM",
                "wednesday": "6:00 AM - 6:00 PM",
                "thursday": "6:00 AM - 6:00 PM",
                "friday": "6:00 AM - 6:00 PM",
                "saturday": "6:00 AM - 6:00 PM",
                "sunday": "6:00 AM - 6:00 PM"
            },
            "amenities": ["Plot rental", "Composting bins", "Tool sharing", "Workshops"],
            "images": [],
            "verified": True,
            "addedBy": "admin",
            "createdAt": timestamp,
            "updatedAt": timestamp
        }
    ]
    
    # Sample locations for Bhaktapur
    bhaktapur_locations = [
        {
            "name": "Bhaktapur Durbar Square Tree Planting",
            "category": "plantation_event",
            "description": "Heritage site beautification with native tree species. Help preserve our cultural heritage while fighting climate change.",
            "city": "Bhaktapur",
            "location": {"type": "Point", "coordinates": [85.4298, 27.6722]},
            "latitude": 27.6722,
            "longitude": 85.4298,
            "address": "Durbar Square, Bhaktapur",
            "contact": {
                "phone": "+977-9860123456",
                "email": "heritage@bhaktapur.org"
            },
            "eventDate": (datetime.now() + timedelta(days=22)).isoformat(),
            "startTime": "06:30 AM",
            "endTime": "11:00 AM",
            "organizer": "Bhaktapur Heritage Society",
            "targetTrees": 200,
            "volunteersNeeded": 50,
            "volunteersRegistered": 28,
            "estimatedCO2Offset": "1.0 ton/year",
            "status": "upcoming",
            "images": [],
            "verified": True,
            "addedBy": "admin",
            "createdAt": timestamp,
            "updatedAt": timestamp
        },
        {
            "name": "Bhaktapur Eco Recycling Hub",
            "category": "recycling_center",
            "description": "Modern recycling facility with sorting services. We pay for recyclable materials and offer free e-waste disposal.",
            "city": "Bhaktapur",
            "location": {"type": "Point", "coordinates": [85.4200, 27.6700]},
            "latitude": 27.6700,
            "longitude": 85.4200,
            "address": "Sallaghari, Bhaktapur",
            "contact": {
                "phone": "+977-1-6610234"
            },
            "hours": {
                "monday": "8:00 AM - 5:00 PM",
                "tuesday": "8:00 AM - 5:00 PM",
                "wednesday": "8:00 AM - 5:00 PM",
                "thursday": "8:00 AM - 5:00 PM",
                "friday": "8:00 AM - 5:00 PM",
                "saturday": "8:00 AM - 2:00 PM"
            },
            "amenities": ["Cash for recyclables", "E-waste disposal", "Bulk pickup"],
            "images": [],
            "verified": True,
            "addedBy": "admin",
            "createdAt": timestamp,
            "updatedAt": timestamp
        },
        {
            "name": "Suryabinayak Community Farm",
            "category": "community_garden",
            "description": "Permaculture demonstration site with organic farming, seed library, and monthly farming workshops.",
            "city": "Bhaktapur",
            "location": {"type": "Point", "coordinates": [85.4400, 27.6650]},
            "latitude": 27.6650,
            "longitude": 85.4400,
            "address": "Suryabinayak, Bhaktapur",
            "contact": {
                "phone": "+977-9849876543",
                "email": "suryafarm@gmail.com"
            },
            "hours": {
                "monday": "7:00 AM - 5:00 PM",
                "tuesday": "7:00 AM - 5:00 PM",
                "wednesday": "7:00 AM - 5:00 PM",
                "thursday": "7:00 AM - 5:00 PM",
                "friday": "7:00 AM - 5:00 PM",
                "saturday": "7:00 AM - 5:00 PM",
                "sunday": "7:00 AM - 12:00 PM"
            },
            "amenities": ["Seed library", "Workshops", "Farm tours", "Organic produce"],
            "images": [],
            "verified": True,
            "addedBy": "admin",
            "createdAt": timestamp,
            "updatedAt": timestamp
        }
    ]
    
    # Sample locations for Lalitpur
    lalitpur_locations = [
        {
            "name": "Patan Green Initiative",
            "category": "ngo_office",
            "description": "Community-based organization promoting urban greening, waste management, and environmental education in Lalitpur.",
            "city": "Lalitpur",
            "location": {"type": "Point", "coordinates": [85.3240, 27.6700]},
            "latitude": 27.6700,
            "longitude": 85.3240,
            "address": "Jawalakhel, Lalitpur",
            "contact": {
                "phone": "+977-1-5522334",
                "email": "info@patangreen.org",
                "website": "https://patangreen.org"
            },
            "hours": {
                "monday": "9:00 AM - 5:00 PM",
                "tuesday": "9:00 AM - 5:00 PM",
                "wednesday": "9:00 AM - 5:00 PM",
                "thursday": "9:00 AM - 5:00 PM",
                "friday": "9:00 AM - 5:00 PM"
            },
            "amenities": ["Volunteer opportunities", "Training programs", "Community events"],
            "images": [],
            "verified": True,
            "addedBy": "admin",
            "createdAt": timestamp,
            "updatedAt": timestamp
        },
        {
            "name": "Godavari Botanical Garden Restoration",
            "category": "plantation_event",
            "description": "Help restore native plant species at Godavari Botanical Garden. Expert botanists will guide the planting process.",
            "city": "Lalitpur",
            "location": {"type": "Point", "coordinates": [85.3900, 27.5900]},
            "latitude": 27.5900,
            "longitude": 85.3900,
            "address": "Godavari, Lalitpur",
            "contact": {
                "phone": "+977-1-5560123",
                "email": "godavari@botanicalgarden.gov.np"
            },
            "eventDate": (datetime.now() + timedelta(days=8)).isoformat(),
            "startTime": "08:00 AM",
            "endTime": "01:00 PM",
            "organizer": "Department of Plant Resources",
            "targetTrees": 300,
            "volunteersNeeded": 75,
            "volunteersRegistered": 62,
            "estimatedCO2Offset": "1.5 tons/year",
            "status": "upcoming",
            "images": [],
            "verified": True,
            "addedBy": "admin",
            "createdAt": timestamp,
            "updatedAt": timestamp
        },
        {
            "name": "Sanepa Organic Store",
            "category": "eco_store",
            "description": "Certified organic grocery store with locally sourced produce, natural cosmetics, and sustainable household products.",
            "city": "Lalitpur",
            "location": {"type": "Point", "coordinates": [85.3100, 27.6850]},
            "latitude": 27.6850,
            "longitude": 85.3100,
            "address": "Sanepa, Lalitpur",
            "contact": {
                "phone": "+977-1-5521234",
                "email": "shop@sanepaorganic.com",
                "website": "https://sanepaorganic.com"
            },
            "hours": {
                "monday": "9:00 AM - 7:00 PM",
                "tuesday": "9:00 AM - 7:00 PM",
                "wednesday": "9:00 AM - 7:00 PM",
                "thursday": "9:00 AM - 7:00 PM",
                "friday": "9:00 AM - 7:00 PM",
                "saturday": "9:00 AM - 7:00 PM",
                "sunday": "10:00 AM - 5:00 PM"
            },
            "amenities": ["Organic certified", "Home delivery", "Bulk discounts"],
            "images": [],
            "verified": True,
            "addedBy": "admin",
            "createdAt": timestamp,
            "updatedAt": timestamp
        },
        {
            "name": "Kupondole Recycling Point",
            "category": "recycling_center",
            "description": "Neighborhood recycling drop-off point. Accepts paper, cardboard, plastic bottles, and aluminum cans.",
            "city": "Lalitpur",
            "location": {"type": "Point", "coordinates": [85.3150, 27.6900]},
            "latitude": 27.6900,
            "longitude": 85.3150,
            "address": "Kupondole, Lalitpur",
            "contact": {
                "phone": "+977-9823456789"
            },
            "hours": {
                "monday": "7:00 AM - 7:00 PM",
                "tuesday": "7:00 AM - 7:00 PM",
                "wednesday": "7:00 AM - 7:00 PM",
                "thursday": "7:00 AM - 7:00 PM",
                "friday": "7:00 AM - 7:00 PM",
                "saturday": "7:00 AM - 7:00 PM",
                "sunday": "7:00 AM - 7:00 PM"
            },
            "amenities": ["24/7 drop-off bins", "Free service"],
            "images": [],
            "verified": True,
            "addedBy": "admin",
            "createdAt": timestamp,
            "updatedAt": timestamp
        },
        {
            "name": "Jhamsikhel Rooftop Garden",
            "category": "community_garden",
            "description": "Urban rooftop garden showcasing vertical farming techniques. Open for community members to learn and participate.",
            "city": "Lalitpur",
            "location": {"type": "Point", "coordinates": [85.3120, 27.6880]},
            "latitude": 27.6880,
            "longitude": 85.3120,
            "address": "Jhamsikhel, Lalitpur",
            "contact": {
                "phone": "+977-9812345678",
                "email": "rooftop@jhamsikhel.com"
            },
            "hours": {
                "monday": "8:00 AM - 6:00 PM",
                "tuesday": "8:00 AM - 6:00 PM",
                "wednesday": "8:00 AM - 6:00 PM",
                "thursday": "8:00 AM - 6:00 PM",
                "friday": "8:00 AM - 6:00 PM",
                "saturday": "8:00 AM - 6:00 PM",
                "sunday": "Closed"
            },
            "amenities": ["Vertical farming demo", "Workshops", "Rooftop tours"],
            "images": [],
            "verified": True,
            "addedBy": "admin",
            "createdAt": timestamp,
            "updatedAt": timestamp
        }
    ]
    
    # Combine all locations
    all_locations = kathmandu_locations + bhaktapur_locations + lalitpur_locations
    
    # Insert into database
    result = eco_locations_collection.insert_many(all_locations)
    
    print(f"✅ Successfully seeded {len(result.inserted_ids)} eco-locations!")
    print(f"   - Kathmandu: {len(kathmandu_locations)} locations")
    print(f"   - Bhaktapur: {len(bhaktapur_locations)} locations")
    print(f"   - Lalitpur: {len(lalitpur_locations)} locations")
    print("\nBreakdown by category:")
    print(f"   - Plantation Events: {sum(1 for loc in all_locations if loc['category'] == 'plantation_event')}")
    print(f"   - Recycling Centers: {sum(1 for loc in all_locations if loc['category'] == 'recycling_center')}")
    print(f"   - Eco Stores: {sum(1 for loc in all_locations if loc['category'] == 'eco_store')}")
    print(f"   - NGO Offices: {sum(1 for loc in all_locations if loc['category'] == 'ngo_office')}")
    print(f"   - Community Gardens: {sum(1 for loc in all_locations if loc['category'] == 'community_garden')}")

if __name__ == "__main__":
    seed_eco_locations()
