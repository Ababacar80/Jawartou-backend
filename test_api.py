import httpx
import json
import asyncio

BASE_URL = "http://localhost:8000/api"


async def test_api():
    async with httpx.AsyncClient() as client:
        print("\n" + "=" * 60)
        print("🧪 TEST API E-COMMERCE")
        print("=" * 60 + "\n")

        # 1. Test Health Check
        print("1️⃣  Test Health Check")
        try:
            response = await client.get("http://localhost:8000/health")
            print(f"✅ Health: {response.json()}\n")
        except Exception as e:
            print(f"❌ Erreur: {e}\n")
            return

        # 2. Registration
        print("2️⃣  Test Registration")
        user_data = {
            "firstName": "Test",
            "lastName": "User",
            "phone": "771234567",
            "password": "password123"
        }
        response = await client.post(f"{BASE_URL}/auth/register", json=user_data)
        if response.status_code == 200:
            reg_data = response.json()
            token = reg_data.get("token")
            user_id = reg_data.get("user", {}).get("id")
            print(f"✅ Inscription réussie")
            print(f"   Token: {token[:30]}...\n")
        else:
            print(f"⚠️  {response.text}\n")
            token = None

        # 3. Login
        if not token:
            print("3️⃣  Test Login")
            login_data = {
                "phone": "771234567",
                "password": "password123"
            }
            response = await client.post(f"{BASE_URL}/auth/login", json=login_data)
            if response.status_code == 200:
                login_result = response.json()
                token = login_result.get("token")
                print(f"✅ Connexion réussie")
                print(f"   Token: {token[:30]}...\n")
            else:
                print(f"❌ {response.text}\n")
                return

        headers = {"Authorization": f"Bearer {token}"}

        # 4. Get Profile
        print("4️⃣  Test Get Profile")
        response = await client.get(f"{BASE_URL}/auth/me", headers=headers)
        if response.status_code == 200:
            profile = response.json().get("data", {})
            print(f"✅ Profil récupéré")
            print(f"   Nom: {profile.get('firstName')} {profile.get('lastName')}")
            print(f"   Téléphone: {profile.get('phone')}")
            print(f"   Rôle: {profile.get('role')}\n")
        else:
            print(f"❌ {response.text}\n")

        # 5. Get Products
        print("5️⃣  Test Get Products")
        response = await client.get(f"{BASE_URL}/products")
        if response.status_code == 200:
            products = response.json()
            print(f"✅ {products.get('count', 0)} produits trouvés\n")
        else:
            print(f"❌ {response.text}\n")

        # 6. Get Cart
        print("6️⃣  Test Get Cart")
        response = await client.get(f"{BASE_URL}/cart", headers=headers)
        if response.status_code == 200:
            cart = response.json().get("data", {})
            print(f"✅ Panier récupéré")
            print(f"   Items: {len(cart.get('items', []))}")
            print(f"   Total: {cart.get('total')}\n")
        else:
            print(f"❌ {response.text}\n")

        print("=" * 60)
        print("✅ Tests complétés!")
        print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(test_api())