from database import Base, engine

print("Tablolar siliniyor...")
Base.metadata.drop_all(bind=engine)
print("Tablolar yeniden oluşturuluyor (embedding kolonu dahil)...")
Base.metadata.create_all(bind=engine)
print("Bitti. Şu tablolar oluştu:")
for tablo in Base.metadata.tables:
    print(f"  - {tablo}")