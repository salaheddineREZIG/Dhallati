
from app import db
from app.lost_and_found.models import Category

# Define your categories and descriptions
categories = [
    {"name": "Electronics", "description": "Devices such as phones, laptops, and accessories."},
    {"name": "Clothing", "description": "Apparel including shirts, pants, jackets, and more."},
    {"name": "Books", "description": "Textbooks, novels, and other reading material."},
    {"name": "Bags", "description": "Backpacks, handbags, and other types of bags."},
    {"name": "Stationery", "description": "Pens, notebooks, and other writing supplies."},
    {"name": "Keys", "description": "Lost keys including car and house keys."},
    {"name": "Jewelry", "description": "Items such as rings, necklaces, and bracelets."},
    {"name": "Sporting Goods", "description": "Equipment and accessories for sports activities."},
    {"name": "Wallets", "description": "Wallets or purses with personal items."},
    {"name": "Personal Items", "description": "Miscellaneous personal items like glasses or watches."},
    {"name": "Others", "description": "Items that do not fit into the other categories."}
]

# Add categories to the database
for category_data in categories:
    category = Category(name=category_data["name"], description=category_data["description"])
    db.session.add(category)

# Commit the transaction to save the categories to the database
db.session.commit()
