import json
import os

# Complete product catalog dataset spanning 10 core commerce domains (280+ items)
CATALOG_ITEMS = [
    # ==========================================
    # DOMAIN 1: CONSUMER ELECTRONICS & AUDIO (28)
    # ==========================================
    {
        "sku": "SONY-WH1000XM5",
        "name": "Sony WH-1000XM5 Wireless Noise Canceling Headphones",
        "description": "Industry-leading active noise canceling over-ear headphones with 2 processors, 8 microphones, 30-hour battery life, and crystal-clear hands-free calling.",
        "category": "Consumer Electronics",
        "price": 348.00,
        "stock": 30,
        "attributes": {"brand": "Sony", "connectivity": "Bluetooth 5.2", "battery_hours": 30, "anc": True, "color": "Silver"}
    },
    {
        "sku": "APPL-AIRPODS-PRO2",
        "name": "Apple AirPods Pro (2nd Generation) USB-C",
        "description": "Wireless in-ear earbuds with up to 2x more Active Noise Cancellation, Adaptive Audio, Transparency mode, and personalized Spatial Audio.",
        "category": "Consumer Electronics",
        "price": 239.00,
        "stock": 50,
        "attributes": {"brand": "Apple", "port": "USB-C", "anc": True, "water_resistant": "IP54"}
    },
    {
        "sku": "BOSE-QC-ULTRA",
        "name": "Bose QuietComfort Ultra Wireless Noise Cancelling Headphones",
        "description": "Spatial audio headphones with CustomTune technology, world-class active noise cancellation, and up to 24 hours of battery life.",
        "category": "Consumer Electronics",
        "price": 429.00,
        "stock": 25,
        "attributes": {"brand": "Bose", "anc": True, "battery_hours": 24, "spatial_audio": True, "color": "Black"}
    },
    {
        "sku": "SAMS-GAL-S24U",
        "name": "Samsung Galaxy S24 Ultra 5G Smartphone 256GB Titanium Gray",
        "description": "Titanium frame flagship smartphone with 6.8-inch Dynamic AMOLED 2X, Snapdragon 8 Gen 3, integrated S-Pen stylus, and 200MP AI camera system.",
        "category": "Consumer Electronics",
        "price": 1199.99,
        "stock": 15,
        "attributes": {"brand": "Samsung", "storage": "256GB", "screen_size": "6.8 inch", "camera_mp": 200, "color": "Titanium Gray"}
    },
    {
        "sku": "APPL-IPHONE15-PRO",
        "name": "Apple iPhone 15 Pro 128GB Natural Titanium",
        "description": "Aerospace-grade titanium design, A17 Pro chip, customizable Action button, USB-C 3.0 connector, and pro 48MP camera system with 3x telephoto.",
        "category": "Consumer Electronics",
        "price": 999.00,
        "stock": 20,
        "attributes": {"brand": "Apple", "storage": "128GB", "material": "Titanium", "chip": "A17 Pro", "color": "Natural Titanium"}
    },
    {
        "sku": "GOOG-PIXEL-8PRO",
        "name": "Google Pixel 8 Pro 5G Smartphone 128GB Obsidian",
        "description": "Google Tensor G3 chip with advanced Google AI, 6.7-inch Super Actua display, pro triple rear camera system with temperature sensor.",
        "category": "Consumer Electronics",
        "price": 799.00,
        "stock": 18,
        "attributes": {"brand": "Google", "storage": "128GB", "chip": "Tensor G3", "camera": "50MP Triple", "color": "Obsidian"}
    },
    {
        "sku": "SONY-A7IV-BODY",
        "name": "Sony Alpha 7 IV Full-Frame Mirrorless Camera Body",
        "description": "33MP full-frame Exmor R CMOS sensor, BIONZ XR processor, 4K 60p 10-bit video, real-time eye AF for humans, animals, and birds.",
        "category": "Consumer Electronics",
        "price": 2498.00,
        "stock": 10,
        "attributes": {"brand": "Sony", "sensor": "Full-Frame 33MP", "mount": "Sony E", "video": "4K 60p"}
    },
    {
        "sku": "DJI-MINI-4PRO",
        "name": "DJI Mini 4 Pro Drone with RC 2 Controller",
        "description": "Ultralight sub-249g folding camera drone with omnidirectional obstacle sensing, 4K/60fps HDR video, 34-minute flight time, and 20km transmission.",
        "category": "Consumer Electronics",
        "price": 959.00,
        "stock": 14,
        "attributes": {"brand": "DJI", "weight_g": 249, "camera": "4K 60fps HDR", "flight_minutes": 34}
    },
    {
        "sku": "KIND-PAPER-16G",
        "name": "Amazon Kindle Paperwhite 16GB 6.8-Inch E-Reader",
        "description": "Glare-free 300 ppi display, adjustable warm light, waterproof IPX8 chassis, USB-C fast charging, and up to 10 weeks of battery life.",
        "category": "Consumer Electronics",
        "price": 149.99,
        "stock": 40,
        "attributes": {"brand": "Amazon", "screen_size": "6.8 inch", "waterproof": True, "battery_weeks": 10}
    },
    {
        "sku": "ANKR-PRIME-27K",
        "name": "Anker Prime 27650mAh Power Bank (250W Total Output)",
        "description": "Multi-device high-capacity portable charger with 2x USB-C ports, 1x USB-A port, smart digital display, and 140W single-port fast charging.",
        "category": "Consumer Electronics",
        "price": 179.99,
        "stock": 35,
        "attributes": {"brand": "Anker", "capacity_mah": 27650, "max_wattage": 250, "ports": 3}
    },
    {
        "sku": "JBL-FLIP-6-BLK",
        "name": "JBL Flip 6 Portable Waterproof Bluetooth Speaker",
        "description": "2-way speaker system with racetrack-shaped woofer, separate tweeter, dual passive radiators, IP67 waterproof and dustproof, 12 hours playtime.",
        "category": "Consumer Electronics",
        "price": 129.95,
        "stock": 45,
        "attributes": {"brand": "JBL", "connectivity": "Bluetooth 5.1", "waterproof_rating": "IP67", "battery_hours": 12, "color": "Midnight Black"}
    },
    {
        "sku": "SONO-ERA-100",
        "name": "Sonos Era 100 Smart Wireless Speaker with Dolby Atmos",
        "description": "Next-gen compact acoustics with stereo sound, deep bass, Bluetooth, Apple AirPlay 2, and built-in voice control.",
        "category": "Consumer Electronics",
        "price": 249.00,
        "stock": 22,
        "attributes": {"brand": "Sonos", "connectivity": "WiFi & Bluetooth", "airplay": True, "voice_control": True, "color": "Matte White"}
    },
    {
        "sku": "GARMIN-FORERUN-965",
        "name": "Garmin Forerunner 965 Premium GPS Running Smartwatch",
        "description": "1.4-inch brilliant AMOLED touchscreen with titanium bezel, built-in full-color mapping, advanced training readiness metrics, and 23-day battery.",
        "category": "Consumer Electronics",
        "price": 599.99,
        "stock": 16,
        "attributes": {"brand": "Garmin", "display": "AMOLED 1.4 inch", "gps": True, "battery_days": 23, "color": "Black/Titanium"}
    },
    {
        "sku": "APPL-WATCH-ULTRA2",
        "name": "Apple Watch Ultra 2 GPS + Cellular 49mm Titanium",
        "description": "Rugged 49mm titanium case, precision dual-frequency GPS, 3000-nit display, depth gauge to 40m, customizable Action button, 36-hour battery.",
        "category": "Consumer Electronics",
        "price": 799.00,
        "stock": 12,
        "attributes": {"brand": "Apple", "case_size": "49mm", "cellular": True, "water_depth_m": 40}
    },
    {
        "sku": "GOOG-PIXEL-BUDS-PRO",
        "name": "Google Pixel Buds Pro Wireless Earbuds Charcoal",
        "description": "Custom 11mm speaker drivers, Active Noise Cancellation with Silent Seal, Transparency mode, multipoint Bluetooth connection, 31-hr battery.",
        "category": "Consumer Electronics",
        "price": 199.99,
        "stock": 30,
        "attributes": {"brand": "Google", "anc": True, "battery_hours": 31, "color": "Charcoal"}
    },
    {
        "sku": "SENN-MOM-4-WHT",
        "name": "Sennheiser Momentum 4 Wireless Over-Ear Headphones",
        "description": "Audiophile-inspired 42mm transducer system, adaptive noise cancellation, customizable sound with built-in EQ, and massive 60-hour battery life.",
        "category": "Consumer Electronics",
        "price": 299.95,
        "stock": 18,
        "attributes": {"brand": "Sennheiser", "battery_hours": 60, "anc": True, "driver_mm": 42, "color": "White/Sand"}
    },
    {
        "sku": "SHURE-SM7B-MIC",
        "name": "Shure SM7B Cardioid Dynamic Vocal Recording Microphone",
        "description": "Legendary studio dynamic vocal microphone with flat, wide-range frequency response, electromagnetic hum shielding, and internal air suspension shock.",
        "category": "Consumer Electronics",
        "price": 399.00,
        "stock": 20,
        "attributes": {"brand": "Shure", "polar_pattern": "Cardioid", "type": "Dynamic XLR", "usage": "Broadcast / Studio"}
    },
    {
        "sku": "ELGATO-STREAM-DECK-MK2",
        "name": "Elgato Stream Deck MK.2 15 LCD Keys Studio Controller",
        "description": "15 customizable tactile LCD keys for controlling apps, audio, lighting, macros, and live streaming workflows with one-touch triggers.",
        "category": "Consumer Electronics",
        "price": 149.99,
        "stock": 32,
        "attributes": {"brand": "Elgato", "keys": 15, "customizable": True, "connection": "USB-C"}
    },
    {
        "sku": "DJI-OSMO-POCKET3",
        "name": "DJI Osmo Pocket 3 Gimbal Camera with 1-Inch CMOS",
        "description": "Pocket-sized handheld 3-axis gimbal camera with 1-inch sensor, 4K/120fps recording, 2-inch rotatable OLED screen, and ActiveTrack 6.0.",
        "category": "Consumer Electronics",
        "price": 519.00,
        "stock": 15,
        "attributes": {"brand": "DJI", "sensor": "1-inch CMOS", "video": "4K 120fps", "gimbal": "3-Axis"}
    },
    {
        "sku": "GOPRO-HERO12-BLK",
        "name": "GoPro HERO12 Black Waterproof Action Camera",
        "description": "5.3K60 and 4K120 HDR video, HyperSmooth 6.0 stabilization, Bluetooth audio support for AirPods, dual LCD screens, and rugged waterproof to 33ft.",
        "category": "Consumer Electronics",
        "price": 399.99,
        "stock": 28,
        "attributes": {"brand": "GoPro", "video": "5.3K 60fps", "waterproof_depth_ft": 33, "stabilization": "HyperSmooth 6.0"}
    },
    {
        "sku": "FUJI-XT5-BODY",
        "name": "Fujifilm X-T5 Mirrorless Digital Camera Body Black",
        "description": "40.2MP X-Trans CMOS 5 HR sensor, 5-axis 7.0-stop in-body image stabilization, classic retro dials, 6.2K/30p video, and 3-way tilting LCD.",
        "category": "Consumer Electronics",
        "price": 1699.95,
        "stock": 8,
        "attributes": {"brand": "Fujifilm", "megapixels": 40.2, "stabilization_stops": 7.0, "mount": "Fujifilm X"}
    },
    {
        "sku": "RODE-WIRELESS-PRO",
        "name": "Rode Wireless PRO Dual-Channel Wireless Microphone System",
        "description": "Dual transmitter and single receiver system with 32-bit float on-board recording, timecode generator, GainAssist, and 260m transmission range.",
        "category": "Consumer Electronics",
        "price": 399.00,
        "stock": 16,
        "attributes": {"brand": "Rode", "channels": 2, "recording_bit": "32-bit Float", "range_m": 260}
    },
    {
        "sku": "MARSH-EMBER-2",
        "name": "Marshall Emberton II Portable Bluetooth Speaker",
        "description": "Compact portable speaker with 30+ hours of playtime, multi-directional 360 sound with True Stereophonic, and IP67 dust and water resistance.",
        "category": "Consumer Electronics",
        "price": 169.99,
        "stock": 24,
        "attributes": {"brand": "Marshall", "battery_hours": 30, "waterproof": "IP67", "color": "Black and Brass"}
    },
    {
        "sku": "BEATS-STUDIO-PRO",
        "name": "Beats Studio Pro Premium Wireless Over-Ear Headphones",
        "description": "Custom acoustic platform with lossless audio via USB-C, personalized spatial audio with dynamic head tracking, active noise cancellation.",
        "category": "Consumer Electronics",
        "price": 249.99,
        "stock": 26,
        "attributes": {"brand": "Beats by Dre", "spatial_audio": True, "anc": True, "battery_hours": 40}
    },
    {
        "sku": "SAMS-T7-SHIELD-2TB",
        "name": "Samsung T7 Shield 2TB Rugged Portable External SSD",
        "description": "High-speed USB 3.2 Gen 2 transfer speeds up to 1050 MB/s, IP65 water and dust resistance, drop resistant up to 3 meters, rubberized exterior.",
        "category": "Consumer Electronics",
        "price": 179.99,
        "stock": 45,
        "attributes": {"brand": "Samsung", "capacity": "2TB", "speed_mbps": 1050, "rugged": True}
    },
    {
        "sku": "ANKR-737-CHARGER",
        "name": "Anker 737 GaNPrime 120W USB-C Fast Wall Charger",
        "description": "Compact high-power GaN wall charger with 2x USB-C ports, 1x USB-A port, PowerIQ 4.0 dynamic power distribution, and ActiveShield 2.0.",
        "category": "Consumer Electronics",
        "price": 74.99,
        "stock": 50,
        "attributes": {"brand": "Anker", "wattage": 120, "technology": "GaNPrime", "ports": 3}
    },
    {
        "sku": "BELK-3IN1-BOOST",
        "name": "Belkin BoostCharge Pro 3-in-1 Wireless MagSafe Charger",
        "description": "15W fast wireless charging stand for iPhone, Apple Watch Ultra fast charging module, and Qi wireless charging pad for AirPods.",
        "category": "Consumer Electronics",
        "price": 149.95,
        "stock": 20,
        "attributes": {"brand": "Belkin", "magsafe": True, "power_w": 15, "compatibility": "Apple ecosystem"}
    },
    {
        "sku": "BOYA-BY-M1-LAV",
        "name": "BOYA BY-M1 Omnidirectional Lavalier Lapel Microphone",
        "description": "Universal clip-on lavalier condenser microphone with 6m cable and 3.5mm TRRS jack for smartphones, DSLRs, audio recorders, and PCs.",
        "category": "Consumer Electronics",
        "price": 19.95,
        "stock": 80,
        "attributes": {"brand": "BOYA", "polar_pattern": "Omnidirectional", "connector": "3.5mm Jack", "cable_length_m": 6}
    },

    # ==========================================
    # DOMAIN 2: COMPUTER HARDWARE & ACCESSORIES (28)
    # ==========================================
    {
        "sku": "LOGI-MX-MST3S",
        "name": "Logitech MX Master 3S Performance Wireless Mouse",
        "description": "Ergonomic wireless mouse with Quiet Clicks, 8000 DPI track-on-glass sensor, MagSpeed electromagnetic scrolling, and multi-device Bluetooth/Logi Bolt support.",
        "category": "Computer Accessories",
        "price": 99.99,
        "stock": 60,
        "attributes": {"brand": "Logitech", "dpi": 8000, "connectivity": "Wireless/Bluetooth", "color": "Graphite"}
    },
    {
        "sku": "KEYCH-Q1-PRO",
        "name": "Keychron Q1 Pro Wireless Custom Mechanical Keyboard",
        "description": "75% layout all-aluminum QMK/VIA wireless mechanical keyboard with hot-swappable Red switches, double-gasket design, and RGB backlighting.",
        "category": "Computer Accessories",
        "price": 199.00,
        "stock": 12,
        "attributes": {"switches": "Gateron Jupiter Red", "layout": "75%", "wireless": True, "material": "CNC Aluminum"}
    },
    {
        "sku": "DELL-U2723QE",
        "name": "Dell UltraSharp 27 4K USB-C Hub Monitor (U2723QE)",
        "description": "27-inch 4K UHD (3840 x 2160) IPS Black monitor with 2000:1 contrast ratio, 98% DCI-P3 color gamut, 90W USB-C Power Delivery hub, and RJ45 ethernet.",
        "category": "Computer Accessories",
        "price": 579.00,
        "stock": 15,
        "attributes": {"resolution": "4K UHD", "panel": "IPS Black", "size_inches": 27, "power_delivery_w": 90}
    },
    {
        "sku": "LOGI-MX-KEYS-S",
        "name": "Logitech MX Keys S Advanced Wireless Illuminated Keyboard",
        "description": "Low-profile scissor keys shaped for fingertips, smart illumination with proximity sensors, customizable Smart Actions macros, multi-OS support.",
        "category": "Computer Accessories",
        "price": 109.99,
        "stock": 45,
        "attributes": {"brand": "Logitech", "switch_type": "Scissor", "backlight": "Smart White", "wireless": True}
    },
    {
        "sku": "APPL-MBP-M3PRO",
        "name": "Apple MacBook Pro 16-Inch M3 Pro (18GB / 512GB SSD) Space Black",
        "description": "Liquid Retina XDR display with ProMotion 120Hz, 12-core CPU, 18-core GPU, up to 22 hours of battery life, MagSafe 3, 3x Thunderbolt 4 ports.",
        "category": "Computer Accessories",
        "price": 2499.00,
        "stock": 8,
        "attributes": {"brand": "Apple", "chip": "M3 Pro", "ram": "18GB", "storage": "512GB", "screen_size": "16 inch"}
    },
    {
        "sku": "DELL-XPS15-9530",
        "name": "Dell XPS 15 9530 Laptop (Intel Core i7-13700H / 16GB / 512GB)",
        "description": "15.6-inch FHD+ 500-nit InfinityEdge display, NVIDIA GeForce RTX 4050 6GB GDDR6, CNC machined aluminum chassis with carbon fiber palm rest.",
        "category": "Computer Accessories",
        "price": 1799.00,
        "stock": 10,
        "attributes": {"brand": "Dell", "cpu": "Core i7-13700H", "gpu": "RTX 4050", "ram": "16GB", "screen_inches": 15.6}
    },
    {
        "sku": "LOGI-BRIO-4K",
        "name": "Logitech Brio 4K Ultra HD Streaming Webcam with HDR",
        "description": "Ultra 4K HD resolution with RightLight 3 auto light correction, dual noise-canceling omnidirectional microphones, Windows Hello infrared facial recognition.",
        "category": "Computer Accessories",
        "price": 159.99,
        "stock": 35,
        "attributes": {"resolution": "4K Ultra HD", "fps": 60, "fov_degrees": 90, "hdr": True}
    },
    {
        "sku": "CALD-TS4-DOCK",
        "name": "CalDigit TS4 Thunderbolt 4 Dock 18-Port Workstation Hub",
        "description": "18 ports of connectivity including 3x Thunderbolt 4, 98W host charging, 2.5GbE Ethernet, UHS-II SD/microSD slots, DisplayPort 1.4, supports 8K display.",
        "category": "Computer Accessories",
        "price": 399.95,
        "stock": 14,
        "attributes": {"brand": "CalDigit", "ports_count": 18, "charging_power_w": 98, "interface": "Thunderbolt 4"}
    },
    {
        "sku": "SAMS-990-PRO-2TB",
        "name": "Samsung 990 PRO PCIe 4.0 NVMe M.2 SSD 2TB",
        "description": "Ultra-fast internal solid state drive with sequential read speeds up to 7450 MB/s, nickel-coated controller for thermal management, ideal for gaming and workstations.",
        "category": "Computer Accessories",
        "price": 169.99,
        "stock": 40,
        "attributes": {"brand": "Samsung", "capacity": "2TB", "read_speed_mbps": 7450, "interface": "PCIe 4.0 NVMe"}
    },
    {
        "sku": "LG-38WN95C-W",
        "name": "LG UltraWide 38-Inch Curved WQHD+ Nano IPS Monitor",
        "description": "3840 x 1600 resolution curved ultrawide monitor with 144Hz refresh rate, 1ms response time, Thunderbolt 3 connectivity, and G-SYNC compatible.",
        "category": "Computer Accessories",
        "price": 1099.99,
        "stock": 6,
        "attributes": {"brand": "LG", "screen_size": "38 inch", "resolution": "3840x1600", "refresh_hz": 144, "curved": True}
    },
    {
        "sku": "ASUS-ROG-AZOTH",
        "name": "ASUS ROG Azoth 75% Wireless Custom Gaming Keyboard",
        "description": "Silicone gasket mount with 3-layer dampening, hot-swappable ROG NX switches, OLED display screen with three-way control knob, tri-mode connection.",
        "category": "Computer Accessories",
        "price": 249.99,
        "stock": 15,
        "attributes": {"brand": "ASUS ROG", "layout": "75%", "display": "OLED", "switches": "ROG NX Red"}
    },
    {
        "sku": "LOGI-LIFT-VERT",
        "name": "Logitech Lift Vertical Ergonomic Wireless Mouse",
        "description": "57-degree natural handshake angle designed for small to medium hands, whisper-quiet clicks, SmartWheel speed scrolling, and textured rubber grip.",
        "category": "Computer Accessories",
        "price": 69.99,
        "stock": 38,
        "attributes": {"brand": "Logitech", "ergonomic_angle": 57, "connectivity": "Bluetooth / Bolt", "color": "Off-White"}
    },
    {
        "sku": "CRUC-T700-1TB",
        "name": "Crucial T700 1TB PCIe Gen5 NVMe M.2 SSD with Heatsink",
        "description": "Blazing fast next-gen storage up to 11700 MB/s sequential read speed, premium aluminum and copper heatsink to dissipate heat efficiently.",
        "category": "Computer Accessories",
        "price": 179.99,
        "stock": 20,
        "attributes": {"brand": "Crucial", "capacity": "1TB", "interface": "PCIe Gen5", "read_speed_mbps": 11700}
    },
    {
        "sku": "CORSAIR-RM850X",
        "name": "Corsair RM850x Fully Modular 850W ATX Power Supply (80+ Gold)",
        "description": "100% all-Japanese 105C capacitors, Zero RPM fan mode for near-silent operation at low to medium loads, fully modular flat black ribbon cables.",
        "category": "Computer Accessories",
        "price": 139.99,
        "stock": 25,
        "attributes": {"brand": "Corsair", "wattage": 850, "efficiency": "80 PLUS Gold", "modular": "Full"}
    },
    {
        "sku": "NZXT-KRAKEN-360",
        "name": "NZXT Kraken Elite 360 RGB AIO Liquid CPU Cooler",
        "description": "360mm radiator with 3x 120mm RGB fans, high-performance Asetek pump, and 2.36-inch wide-angle LCD display for system temps and custom GIFs.",
        "category": "Computer Accessories",
        "price": 279.99,
        "stock": 12,
        "attributes": {"brand": "NZXT", "radiator_size_mm": 360, "screen": "2.36 inch LCD", "lighting": "RGB"}
    },
    {
        "sku": "ANKR-555-USB-HUB",
        "name": "Anker 555 8-in-1 USB-C Hub with 100W Power Delivery",
        "description": "Compact aluminum hub with 4K@60Hz HDMI, 100W Power Delivery USB-C, 1Gbps Ethernet, 2x USB-A 3.2 10Gbps data ports, and SD/microSD card reader.",
        "category": "Computer Accessories",
        "price": 69.99,
        "stock": 50,
        "attributes": {"brand": "Anker", "ports": 8, "hdmi": "4K@60Hz", "power_delivery_w": 100}
    },
    {
        "sku": "RAZR-DEATH-V3PRO",
        "name": "Razer DeathAdder V3 Pro Ultra-Lightweight Wireless Gaming Mouse",
        "description": "63g ultra-lightweight ergonomic esports design, Focus Pro 30K optical sensor, Gen-3 optical mouse switches, up to 90 hours battery life.",
        "category": "Computer Accessories",
        "price": 149.99,
        "stock": 28,
        "attributes": {"brand": "Razer", "weight_g": 63, "sensor_dpi": 30000, "battery_hours": 90}
    },
    {
        "sku": "SAMS-VIEWFIN-S9",
        "name": "Samsung 27-Inch ViewFinity S9 5K Studio Display (5120 x 2880)",
        "description": "Matte display 5K IPS panel with 99% DCI-P3, factory color calibrated, 4K SlimFit camera included, Thunderbolt 4 90W charging, Smart TV apps.",
        "category": "Computer Accessories",
        "price": 1299.99,
        "stock": 7,
        "attributes": {"brand": "Samsung", "resolution": "5K 5120x2880", "panel": "Matte IPS", "size_inches": 27}
    },
    {
        "sku": "NUPHY-AIR75-V2",
        "name": "NuPhy Air75 V2 Ultra-Slim Wireless Mechanical Keyboard",
        "description": "Low-profile 75% mechanical keyboard with Gateron Low-Profile 2.0 switches, QMK/VIA programmable, 1000Hz polling rate in 2.4G wireless mode.",
        "category": "Computer Accessories",
        "price": 119.95,
        "stock": 30,
        "attributes": {"brand": "NuPhy", "layout": "75% Low-Profile", "polling_hz": 1000, "weight_g": 598}
    },
    {
        "sku": "WEST-SN850X-4TB",
        "name": "WD_BLACK SN850X 4TB NVMe M.2 PCIe Gen4 Internal Gaming SSD",
        "description": "Top-tier PCIe Gen4 storage with sustained speeds up to 7300 MB/s, Game Mode 2.0 predictive loading, enormous 4TB capacity for heavy libraries.",
        "category": "Computer Accessories",
        "price": 299.99,
        "stock": 16,
        "attributes": {"brand": "Western Digital", "capacity": "4TB", "read_speed_mbps": 7300, "interface": "PCIe 4.0"}
    },
    {
        "sku": "LOGI-MX-ERGO",
        "name": "Logitech MX ERGO Wireless Trackball Mouse with Adjustable Hinge",
        "description": "Advanced trackball mouse with 0 or 20 degree adjustable hinge, precision mode tracking button, sculpted ergonomic palm rest, 4-month battery life.",
        "category": "Computer Accessories",
        "price": 89.99,
        "stock": 22,
        "attributes": {"brand": "Logitech", "type": "Trackball", "angle_degrees": 20, "battery_rechargeable": True}
    },
    {
        "sku": "BENQ-SCREENBAR-PRO",
        "name": "BenQ ScreenBar Pro Automatic Eye-Care LED Monitor Light",
        "description": "Asymmetric optical design prevents screen glare, ultrasonic motion sensor for auto on/off, auto-dimming ambient light sensor, CRI>95 color fidelity.",
        "category": "Computer Accessories",
        "price": 139.00,
        "stock": 35,
        "attributes": {"brand": "BenQ", "cri": 95, "anti_glare": True, "motion_sensor": True}
    },
    {
        "sku": "UGRN-REVODOK-PRO",
        "name": "UGREEN Revodok Pro 109 9-in-1 Dual 4K HDMI USB-C Hub",
        "description": "Dual 4K@60Hz HDMI video output, 100W PD passthrough charging, 5Gbps USB-A 3.0 ports, Gigabit Ethernet port, and SD/TF card slots in aluminum body.",
        "category": "Computer Accessories",
        "price": 49.99,
        "stock": 60,
        "attributes": {"brand": "UGREEN", "video_out": "Dual 4K HDMI", "pd_wattage": 100, "ports": 9}
    },
    {
        "sku": "ELGATO-WAVE-3-MIC",
        "name": "Elgato Wave:3 Premium USB Condenser Microphone",
        "description": "Cardioid condenser capsule with 24-bit 96kHz analog-to-digital converter, proprietary Clipguard anti-distortion tech, and Wave Link multi-channel mixing software.",
        "category": "Computer Accessories",
        "price": 149.99,
        "stock": 24,
        "attributes": {"brand": "Elgato", "connection": "USB-C", "bitrate": "24-bit/96kHz", "anti_distortion": True}
    },
    {
        "sku": "CORSAIR-VENG-32GB",
        "name": "Corsair Vengeance RGB DDR5 RAM 32GB (2x16GB) 6000MHz CL30",
        "description": "High-performance DDR5 desktop memory with onboard voltage regulation, custom Intel XMP 3.0 / AMD EXPO profiles, and panoramic ten-zone RGB lighting.",
        "category": "Computer Accessories",
        "price": 124.99,
        "stock": 40,
        "attributes": {"brand": "Corsair", "capacity": "32GB", "speed_mhz": 6000, "timing": "CL30", "type": "DDR5"}
    },
    {
        "sku": "LOGI-MEGABOOM-MAT",
        "name": "Logitech Studio Series XL Anti-Fray Desk Mat Pad (Dark Rose)",
        "description": "Spill-resistant microfiber cloth surface with fine-stitched edges and anti-slip rubber base for smooth effortless mouse gliding and desk protection.",
        "category": "Computer Accessories",
        "price": 19.99,
        "stock": 70,
        "attributes": {"brand": "Logitech", "size": "XL (70x30cm)", "spill_resistant": True, "color": "Dark Rose"}
    },
    {
        "sku": "SATE-STAND-HUB",
        "name": "Satechi Type-C Aluminum Stand & Hub for Mac Mini / Studio",
        "description": "Sleek matching aluminum enclosure stand for Mac Mini with built-in M.2 SATA SSD enclosure, front USB-C, USB-A, micro/SD card readers, and 3.5mm jack.",
        "category": "Computer Accessories",
        "price": 99.99,
        "stock": 18,
        "attributes": {"brand": "Satechi", "material": "Space Gray Aluminum", "internal_ssd_slot": "M.2 SATA"}
    },
    {
        "sku": "KENS-PRO-FIT-BALL",
        "name": "Kensington Expert Wireless Trackball Mouse with Scroll Ring",
        "description": "Large 55mm red trackball with patented scroll ring for effortless page scrolling, dual wireless 2.4GHz and Bluetooth 4.0, detachable ergonomic wrist rest.",
        "category": "Computer Accessories",
        "price": 84.99,
        "stock": 15,
        "attributes": {"brand": "Kensington", "ball_diameter_mm": 55, "wrist_rest": True, "scroll_ring": True}
    },

    # ==========================================
    # DOMAIN 3: APPAREL & FASHION (30)
    # ==========================================
    {
        "sku": "SKU-4471",
        "name": "Cozy Oversized Knit Sweater",
        "description": "Ultra-soft chunky knit oversized sweater crafted from 100% merino wool blend. Perfect for cold winter days, casual layering, and cozy loungewear.",
        "category": "Apparel & Fashion",
        "price": 58.50,
        "stock": 45,
        "attributes": {"color": "Oatmeal Beige", "size": "L", "material": "Merino Wool Blend", "gender": "Unisex"}
    },
    {
        "sku": "SKU-4472",
        "name": "Vintage Corduroy Button-Down Shirt",
        "description": "Retro relaxed-fit corduroy long-sleeve shirt in deep forest green. Breathable cotton construction with chest pocket.",
        "category": "Apparel & Fashion",
        "price": 42.00,
        "stock": 25,
        "attributes": {"color": "Forest Green", "size": "M", "material": "100% Cotton Corduroy"}
    },
    {
        "sku": "PATAG-DWN-882",
        "name": "Alpine Ultralight Down Jacket",
        "description": "800-fill-power water-resistant goose down jacket. Packable into its own pocket, windproof ripstop nylon shell for extreme mountaineering.",
        "category": "Apparel & Fashion",
        "price": 229.00,
        "stock": 18,
        "attributes": {"color": "Matte Black", "size": "L", "rating": 4.9, "waterproof": True}
    },
    {
        "sku": "ARCT-BETA-LT-JKT",
        "name": "Arc'teryx Beta LT GORE-TEX Mountain Jacket",
        "description": "Lightweight, versatile, waterproof 3L GORE-TEX shell jacket with helmet compatible StormHood and WaterTight pit zippers for alpine adventures.",
        "category": "Apparel & Fashion",
        "price": 450.00,
        "stock": 12,
        "attributes": {"brand": "Arc'teryx", "material": "3L GORE-TEX", "waterproof": True, "size": "L", "color": "Black Sapphire"}
    },
    {
        "sku": "LULU-ALIGN-PNT25",
        "name": "Lululemon Align High-Rise Yoga Pant 25-Inch",
        "description": "Buttery-soft Nulu fabric yoga leggings that feel weightless, featuring four-way stretch, sweat-wicking properties, and hidden waistband pocket.",
        "category": "Apparel & Fashion",
        "price": 98.00,
        "stock": 65,
        "attributes": {"brand": "Lululemon", "fabric": "Nulu", "inseam_inches": 25, "size": "S", "color": "True Navy"}
    },
    {
        "sku": "LEVI-501-ORIG-DNM",
        "name": "Levi's 501 Original Fit Straight Leg Denim Jeans",
        "description": "The timeless icon straight-fit jeans with signature button fly, regular fit through thigh, and durable 100% heavyweight cotton denim.",
        "category": "Apparel & Fashion",
        "price": 79.50,
        "stock": 55,
        "attributes": {"brand": "Levi's", "fit": "Straight", "waist": 32, "length": 32, "material": "100% Cotton"}
    },
    {
        "sku": "CHAMP-REV-WEAVE-HD",
        "name": "Champion Reverse Weave Heavyweight Fleece Hoodie",
        "description": "Classic 12oz heavyweight fleece pullover hoodie cut on the cross-grain to resist vertical shrinkage, with ribbed side panels for mobility.",
        "category": "Apparel & Fashion",
        "price": 65.00,
        "stock": 40,
        "attributes": {"brand": "Champion", "weight_oz": 12, "material": "Cotton/Poly Fleece", "size": "XL", "color": "Oxford Gray"}
    },
    {
        "sku": "UNIQ-CASH-CRW-SWT",
        "name": "100% Pure Cashmere Crewneck Sweater",
        "description": "Luxuriously soft and warm crewneck sweater spun from 100% premium grade cashmere yarn, lightweight warmth with ribbed cuffs and hem.",
        "category": "Apparel & Fashion",
        "price": 129.90,
        "stock": 28,
        "attributes": {"material": "100% Cashmere", "neckline": "Crewneck", "size": "M", "color": "Charcoal Melange"}
    },
    {
        "sku": "TNF-NUPTSE-1996",
        "name": "The North Face 1996 Retro Nuptse Down Jacket",
        "description": "Iconic boxy silhouette puffer jacket with 700-fill goose down insulation, durable water-repellent DWR finish, and stowable hood.",
        "category": "Apparel & Fashion",
        "price": 330.00,
        "stock": 15,
        "attributes": {"brand": "The North Face", "insulation": "700 Fill Goose Down", "size": "L", "color": "TNF Black"}
    },
    {
        "sku": "BARB-BEDALE-WAX",
        "name": "Barbour Classic Bedale Waxed Cotton Jacket",
        "description": "Traditional British heritage waxed jacket with corduroy collar, storm fly front, tartan cotton lining, and bellow pockets for country or city wear.",
        "category": "Apparel & Fashion",
        "price": 395.00,
        "stock": 10,
        "attributes": {"brand": "Barbour", "material": "Waxed Cotton", "lining": "Cotton Tartan", "color": "Olive"}
    },
    {
        "sku": "PATAG-SYNCH-SNAP",
        "name": "Patagonia Lightweight Synchilla Snap-T Fleece Pullover",
        "description": "Warm, durable 100% recycled polyester fleece pullover with nylon chest pocket flap and 4-snap placket stand-up collar.",
        "category": "Apparel & Fashion",
        "price": 139.00,
        "stock": 30,
        "attributes": {"brand": "Patagonia", "material": "Recycled Synchilla Fleece", "size": "M", "color": "Nickel w/ Navy"}
    },
    {
        "sku": "VUORI-KORE-SHRT",
        "name": "Vuori Kore Athletic Lined Workout Shorts 7.5-Inch",
        "description": "Classic athletic shorts with breathable boxer-brief liner, 4-way stretch moisture-wicking fabric, and anti-odor technology.",
        "category": "Apparel & Fashion",
        "price": 68.00,
        "stock": 48,
        "attributes": {"brand": "Vuori", "inseam_inches": 7.5, "liner": "Built-in Boxer-Brief", "size": "M", "color": "Oregano"}
    },
    {
        "sku": "EVERL-PIMA-TEE-3PK",
        "name": "Everlane Premium Organic Pima Cotton T-Shirt 3-Pack",
        "description": "Ultra-soft long-staple organic Peruvian Pima cotton classic crewneck tees with reinforced stitching and clean pre-shrunk finish.",
        "category": "Apparel & Fashion",
        "price": 75.00,
        "stock": 50,
        "attributes": {"brand": "Everlane", "pack_count": 3, "material": "100% Organic Pima Cotton", "size": "L"}
    },
    {
        "sku": "RALPH-SLIM-OXF-SHT",
        "name": "Polo Ralph Lauren Slim Fit Oxford Cotton Shirt",
        "description": "Classic long-sleeve button-down collar shirt crafted from durable garment-washed cotton Oxford cloth with signature embroidered Pony.",
        "category": "Apparel & Fashion",
        "price": 115.00,
        "stock": 35,
        "attributes": {"brand": "Ralph Lauren", "fit": "Slim Fit", "material": "100% Cotton Oxford", "color": "Light Blue"}
    },
    {
        "sku": "GYMSH-VITAL-SEAM-TGT",
        "name": "Gymshark Vital Seamless 2.0 High-Waisted Leggings",
        "description": "Form-enhancing seamless knit gym leggings with physique-contouring shading, sweat-wicking finish, and compressive high waistband.",
        "category": "Apparel & Fashion",
        "price": 54.00,
        "stock": 60,
        "attributes": {"brand": "Gymshark", "construction": "Seamless Knit", "size": "S", "color": "Smokey Grey Marl"}
    },
    {
        "sku": "CARH-B01-DBLKNEE",
        "name": "Carhartt Firm Duck Double-Front Work Pant Dungaree",
        "description": "Heavyweight 12-ounce 100% ring-spun cotton duck work pants with double knees for knee pads and multiple utility tool pockets.",
        "category": "Apparel & Fashion",
        "price": 59.99,
        "stock": 40,
        "attributes": {"brand": "Carhartt", "material": "12oz Cotton Duck", "reinforced": "Double Knee", "color": "Carhartt Brown"}
    },
    {
        "sku": "SMART-MERIN-250-TOP",
        "name": "Smartwool Classic Thermal Merino 250 Base Layer Crew",
        "description": "100% Merino wool interlocking knit thermal base layer providing superior breathable insulation, moisture management, and natural odor resistance.",
        "category": "Apparel & Fashion",
        "price": 115.00,
        "stock": 25,
        "attributes": {"brand": "Smartwool", "fabric_weight": "250g/m2", "material": "100% Merino Wool", "size": "M"}
    },
    {
        "sku": "MACK-WLL-VIBE-VAP",
        "name": "Mack Weldon Stealth Windproof Insulated Commuter Vest",
        "description": "Streamlined technical commuter vest with high-loft Therma-Fil insulation, water-resistant stretch shell, and hidden passport zipper pocket.",
        "category": "Apparel & Fashion",
        "price": 148.00,
        "stock": 20,
        "attributes": {"brand": "Mack Weldon", "water_resistant": True, "size": "L", "color": "Total Eclipse Navy"}
    },
    {
        "sku": "FILSON-MACK-CRUIS",
        "name": "Filson Mackinaw 100% Virgin Wool Cruiser Jacket",
        "description": "Heavy-duty 24-oz 100% virgin Mackinaw wool jacket with dual-entry rear map pocket, 4 front utility pockets, wind-blocking naturally water-repellent warmth.",
        "category": "Apparel & Fashion",
        "price": 495.00,
        "stock": 8,
        "attributes": {"brand": "Filson", "material": "24oz Virgin Wool", "color": "Red/Black Plaid", "made_in": "USA"}
    },
    {
        "sku": "RAYB-WAYFAR-2140",
        "name": "Ray-Ban Original Wayfarer Classic Sunglasses (Polarized)",
        "description": "Iconic acetate frames with polarized G-15 green crystal lenses providing 100% UV protection, distinct temple shape, and durable five-barrel hinges.",
        "category": "Apparel & Fashion",
        "price": 215.00,
        "stock": 30,
        "attributes": {"brand": "Ray-Ban", "lens": "Polarized G-15", "frame": "Polished Black Acetate", "uv_protection": "100% UV400"}
    },
    {
        "sku": "BELL-TRANS-BPACK",
        "name": "Bellroy Transit Work Backpack 20L Water-Resistant",
        "description": "Clean modern commuter backpack with dedicated 16-inch laptop compartment, quick-access sunglasses pocket, internal water bottle sleeve, and recycled fabric.",
        "category": "Apparel & Fashion",
        "price": 179.00,
        "stock": 22,
        "attributes": {"brand": "Bellroy", "capacity_liters": 20, "laptop_size_inches": 16, "material": "Recycled Baida Nylon"}
    },
    {
        "sku": "STAN-RUG-LEATH-BLT",
        "name": "Full-Grain Italian Leather Casual Dress Belt",
        "description": "Handcrafted 1.5-inch solid full-grain vegetable-tanned Italian bridle leather belt with brushed stainless steel roller buckle and beveled burnished edges.",
        "category": "Apparel & Fashion",
        "price": 48.00,
        "stock": 45,
        "attributes": {"material": "Full-Grain Italian Leather", "width_inches": 1.5, "color": "Cognac Brown", "size": "34"}
    },
    {
        "sku": "DARN-TOUGH-HK-SCK",
        "name": "Darn Tough Hiker Micro Crew Midweight Cushion Socks",
        "description": "Guaranteed for life Merino wool blend hiking socks with seamless toe box, dense high-density cushioning underfoot, and breathable performance fit.",
        "category": "Apparel & Fashion",
        "price": 25.00,
        "stock": 80,
        "attributes": {"brand": "Darn Tough", "material": "Merino Wool Blend", "cushioning": "Midweight", "warranty": "Lifetime Guarantee"}
    },
    {
        "sku": "REI-COOP-RAIN-JKT",
        "name": "REI Co-op Trailmade Waterproof Rain Jacket",
        "description": "Packable 2-layer waterproof/breathable ripstop nylon shell with fully taped seams, adjustable hood, and underarm pit zips for budget backcountry rain protection.",
        "category": "Apparel & Fashion",
        "price": 69.95,
        "stock": 35,
        "attributes": {"brand": "REI Co-op", "waterproof": True, "weight_oz": 13, "color": "Sunflare Gold", "size": "M"}
    },
    {
        "sku": "ALOY-WAR-HOOD-BLK",
        "name": "Alo Yoga Conquer Performance Pullover Hoodie",
        "description": "French terry lightweight athletic stretch hoodie designed with raglan sleeves for full mobility, side zipper pockets, and moisture-wicking finish.",
        "category": "Apparel & Fashion",
        "price": 108.00,
        "stock": 26,
        "attributes": {"brand": "Alo Yoga", "fabric": "French Terry Stretch", "size": "L", "color": "Solid Black"}
    },
    {
        "sku": "TILL-LTM6-AIR-HAT",
        "name": "Tilley LTM6 Airflo Sun Protection Outdoor Hat",
        "description": "UPF 50+ sun protection hat with 3/4-inch mesh crown for maximum airflow, water-repellent finish, secret crown pocket, and buoyant foam core.",
        "category": "Apparel & Fashion",
        "price": 99.00,
        "stock": 20,
        "attributes": {"brand": "Tilley", "sun_protection": "UPF 50+", "floats": True, "color": "Khaki with Olive"}
    },
    {
        "sku": "KAVU-ROPE-BAG-ORG",
        "name": "KAVU Original Cotton Canvas Rope Sling Bag 10L",
        "description": "Signature crossbody sling pack with adjustable rope shoulder strap, two vertical zip compartments, two external phone pockets, and rugged 12oz cotton canvas.",
        "category": "Apparel & Fashion",
        "price": 55.00,
        "stock": 42,
        "attributes": {"brand": "KAVU", "capacity_liters": 10, "material": "12oz Cotton Canvas", "strap": "Climbing Rope"}
    },
    {
        "sku": "OUTD-RES-FERR-PNT",
        "name": "Outdoor Research Ferrosi Lightweight Hiking Pant",
        "description": "Breathable 90D stretch-woven softshell pants with UPF 50+ sun rating, wind resistance, quick-dry nylon blend, and articulated knees for mobility.",
        "category": "Apparel & Fashion",
        "price": 89.00,
        "stock": 30,
        "attributes": {"brand": "Outdoor Research", "material": "Ferrosi Softshell", "stretch": "4-Way", "size": "32x32"}
    },
    {
        "sku": "PEND-NAT-PRK-BLNK",
        "name": "Pendleton Yakima Camp Pure Virgin Wool Blanket (Queen)",
        "description": "Heirloom-quality pure virgin wool and cotton blend camp blanket inspired by historic American national parks, woven in American Pacific Northwest mills.",
        "category": "Apparel & Fashion",
        "price": 199.00,
        "stock": 14,
        "attributes": {"brand": "Pendleton", "size": "Queen (90x90 in)", "material": "86% Virgin Wool / 14% Cotton", "made_in": "USA"}
    },
    {
        "sku": "AER-CITY-SLING2-X",
        "name": "Aer City Sling 2 X-Pac Everyday Carry Crossbody Bag",
        "description": "Waterproof dimension-polyant VX-42 X-Pac sailcloth sling bag with Fidlock magnetic buckle, YKK AquaGuard zippers, and organized EDC tech pockets.",
        "category": "Apparel & Fashion",
        "price": 115.00,
        "stock": 25,
        "attributes": {"brand": "Aer", "fabric": "VX-42 X-Pac", "capacity_liters": 2.5, "waterproof_zippers": True}
    },

    # ==========================================
    # DOMAIN 4: FOOTWEAR & OUTDOOR GEAR (28)
    # ==========================================
    {
        "sku": "HOKA-CLIF-9-WHT",
        "name": "Hoka Clifton 9 Lightweight Daily Running Shoe",
        "description": "Signature maximalist road running shoe with responsive compression molded EVA foam, early-stage Meta-Rocker for smooth stride transition, and breathable knit upper.",
        "category": "Footwear & Outdoor",
        "price": 145.00,
        "stock": 35,
        "attributes": {"brand": "Hoka", "cushion": "Max Plush", "drop_mm": 5, "size": "10.5", "color": "White / Nimbus Cloud"}
    },
    {
        "sku": "ON-CLOUD-5-BLK",
        "name": "On Running Cloud 5 All-Day Performance Sneaker",
        "description": "Ultralight everyday sneaker with patented CloudTec cushioning in Zero-Gravity foam, speed-lacing system, and 44% recycled breathable antimicrobial mesh.",
        "category": "Footwear & Outdoor",
        "price": 139.99,
        "stock": 40,
        "attributes": {"brand": "On Running", "technology": "CloudTec", "weight_g": 250, "size": "10", "color": "All Black"}
    },
    {
        "sku": "SALO-SPEED-CROSS6",
        "name": "Salomon Speedcross 6 GORE-TEX Trail Running Shoe",
        "description": "Aggressive Mud Contagrip lugged outsole for deep traction on technical muddy trails, waterproof GORE-TEX membrane, and Quicklace one-pull harness.",
        "category": "Footwear & Outdoor",
        "price": 160.00,
        "stock": 22,
        "attributes": {"brand": "Salomon", "waterproof": "GORE-TEX", "lug_depth_mm": 5, "size": "11"}
    },
    {
        "sku": "ALTR-LONE-PEAK-7",
        "name": "Altra Lone Peak 7 Zero-Drop Trail Runner",
        "description": "Trail running shoe featuring Altra signature FootShape toe box for natural toe splay, Zero-Drop balanced cushioning, MaxTrac grip outsole, and StoneGuard rock plate.",
        "category": "Footwear & Outdoor",
        "price": 150.00,
        "stock": 25,
        "attributes": {"brand": "Altra", "drop_mm": 0, "toe_box": "FootShape Wide", "size": "10.5"}
    },
    {
        "sku": "LOWA-RENEG-GTX-MID",
        "name": "Lowa Renegade GTX Mid Waterproof Hiking Boot",
        "description": "Nubuck leather upper with waterproof GORE-TEX lining, Monowrap frame for lateral stability, and Vibram Evo outsole for rocky backpacking trails.",
        "category": "Footwear & Outdoor",
        "price": 255.00,
        "stock": 16,
        "attributes": {"brand": "Lowa", "material": "Nubuck Leather / GORE-TEX", "outsole": "Vibram Evo", "size": "10.5 D"}
    },
    {
        "sku": "BIRK-ARIZ-LEATH-B",
        "name": "Birkenstock Arizona Unisex Leather Two-Strap Sandal",
        "description": "Iconic double adjustable buckle strap sandal with anatomically shaped natural cork-latex footbed, oiled leather upper, and shock-absorbing EVA sole.",
        "category": "Footwear & Outdoor",
        "price": 130.00,
        "stock": 50,
        "attributes": {"brand": "Birkenstock", "footbed": "Natural Cork-Latex", "material": "Oiled Leather", "color": "Habana Brown", "size": "42 EU"}
    },
    {
        "sku": "BLUND-500-STOUT",
        "name": "Blundstone Original 500 Series Chelsea Leather Boot",
        "description": "Rugged Australian elastic-sided Chelsea boot crafted from premium water-resistant stout brown leather with XRD Technology shock absorption in heel.",
        "category": "Footwear & Outdoor",
        "price": 219.95,
        "stock": 20,
        "attributes": {"brand": "Blundstone", "style": "Chelsea Boot", "leather": "Premium Water-Resistant", "color": "Stout Brown"}
    },
    {
        "sku": "REDW-IRON-8111",
        "name": "Red Wing Heritage Iron Ranger 6-Inch Leather Work Boot",
        "description": "Handcrafted in USA with rich Amber Harness oil-tanned leather, double-layer leather toe cap, Goodyear welt construction, and Vibram 430 Mini-Lug sole.",
        "category": "Footwear & Outdoor",
        "price": 349.99,
        "stock": 10,
        "attributes": {"brand": "Red Wing", "construction": "Goodyear Welt", "leather": "Amber Harness", "made_in": "USA", "size": "10 D"}
    },
    {
        "sku": "TEVA-HURR-XLT2",
        "name": "Teva Hurricane XLT2 Water Sandal (Rapid Dry Webbing)",
        "description": "Versatile water-ready outdoor adventure sandal with quick-dry REPREVE recycled polyester webbing straps, cushioned EVA footbed, and Durabrasion rubber outsole.",
        "category": "Footwear & Outdoor",
        "price": 75.00,
        "stock": 38,
        "attributes": {"brand": "Teva", "waterproof": True, "recycled": True, "size": "10", "color": "Black"}
    },
    {
        "sku": "OSPR-ATMO-AG65",
        "name": "Osprey Atmos AG 65 Backpacking Backpack (Anti-Gravity)",
        "description": "Revolutionary Anti-Gravity continuous backpanel suspension system, Fit-on-the-Fly custom hipbelt, integrated raincover, and trekking pole attachment.",
        "category": "Footwear & Outdoor",
        "price": 340.00,
        "stock": 14,
        "attributes": {"brand": "Osprey", "capacity_liters": 65, "suspension": "Anti-Gravity Mesh", "weight_kg": 2.1}
    },
    {
        "sku": "MSR-HUBBA-NX2",
        "name": "MSR Hubba Hubba 2-Person Ultralight Backpacking Tent",
        "description": "Freestanding 3-season tent weighing only 2 lbs 14 oz with DuraShield waterproof coating, Easton Syclone unbreakable composite poles, and dual StayDry doors.",
        "category": "Footwear & Outdoor",
        "price": 479.95,
        "stock": 12,
        "attributes": {"brand": "MSR", "capacity": "2-Person", "min_weight_lbs": 2.88, "seasons": 3}
    },
    {
        "sku": "THERM-NEO-AIR-NXT",
        "name": "Therm-a-Rest NeoAir XLite NXT Ultralight Sleeping Pad",
        "description": "3-inch thick 4.5 R-value insulated backpacking mattress with ThermaCapture reflective tech, packs down to the size of a 1L water bottle, weighs 13 oz.",
        "category": "Footwear & Outdoor",
        "price": 209.95,
        "stock": 18,
        "attributes": {"brand": "Therm-a-Rest", "r_value": 4.5, "thickness_inches": 3.0, "weight_oz": 13}
    },
    {
        "sku": "JETBOIL-FLASH-SYS",
        "name": "Jetboil Flash Fast Backpacking Camping Cooking System",
        "description": "Integrated 1.0L FluxRing cooking cup boils water in a blazing 100 seconds, push-button piezoelectric igniter, and color-changing thermal heat indicator.",
        "category": "Footwear & Outdoor",
        "price": 129.95,
        "stock": 25,
        "attributes": {"brand": "Jetboil", "boil_time_sec": 100, "capacity_liters": 1.0, "weight_oz": 13.1}
    },
    {
        "sku": "BLKD-STORM-500R",
        "name": "Black Diamond Storm 500-R Rechargeable LED Headlamp",
        "description": "500-lumen output headlamp with BD 1500 rechargeable Li-ion battery, PowerTap instant brightness adjustment, IP67 waterproof rating, and RGB night vision LEDs.",
        "category": "Footwear & Outdoor",
        "price": 74.95,
        "stock": 40,
        "attributes": {"brand": "Black Diamond", "lumens": 500, "waterproof": "IP67", "battery": "Rechargeable Lithium"}
    },
    {
        "sku": "HYDR-WIDE-FLX-32",
        "name": "Hydro Flask 32 oz Wide Mouth Insulated Water Bottle",
        "description": "TempShield double-wall vacuum insulation keeps drinks ice cold for 24 hours or hot for 12, made with pro-grade 18/8 stainless steel and leakproof Flex Cap.",
        "category": "Footwear & Outdoor",
        "price": 44.95,
        "stock": 65,
        "attributes": {"brand": "Hydro Flask", "capacity_oz": 32, "insulation_hours_cold": 24, "color": "Pacific Blue"}
    },
    {
        "sku": "SAWY-SQUEE-FILT",
        "name": "Sawyer Squeeze Portable Water Filtration System",
        "description": "0.1-micron absolute hollow fiber membrane inline water filter removes 99.99999% of bacteria and protozoa, includes two 32oz reusable pouches.",
        "category": "Footwear & Outdoor",
        "price": 40.95,
        "stock": 55,
        "attributes": {"brand": "Sawyer", "filtration_micron": 0.1, "capacity_gallons": 100000, "weight_oz": 3.0}
    },
    {
        "sku": "NEMO-DISCO-15-DWN",
        "name": "NEMO Disco 15F 650FP Down Sleeping Bag (Spoon Shape)",
        "description": "Classic spoon-shape design contoured for side sleepers with Thermo Gills temperature regulation vents, 650-fill hydrophobic down, and waterproof toe box.",
        "category": "Footwear & Outdoor",
        "price": 319.95,
        "stock": 10,
        "attributes": {"brand": "NEMO", "temp_rating_f": 15, "insulation": "650 Fill Down", "fit": "Side Sleeper Spoon"}
    },
    {
        "sku": "GARMIN-INREACH-MINI2",
        "name": "Garmin inReach Mini 2 Lightweight Satellite Communicator",
        "description": "Compact two-way satellite communicator with 100% global Iridium network coverage, interactive SOS to emergency monitoring center, and TracBack routing.",
        "category": "Footwear & Outdoor",
        "price": 399.99,
        "stock": 15,
        "attributes": {"brand": "Garmin", "satellite_network": "Iridium Global", "battery_days": 14, "sos_enabled": True}
    },
    {
        "sku": "LEATH-WAVE-PLUS",
        "name": "Leatherman Wave+ 18-in-1 All-Locking Multi-Tool",
        "description": "International best-selling multi-tool with replaceable premium wire cutters, 420HC knife blades, wood/metal file, saw, large bit driver, and nylon sheath.",
        "category": "Footwear & Outdoor",
        "price": 119.95,
        "stock": 30,
        "attributes": {"brand": "Leatherman", "tools_count": 18, "material": "Stainless Steel", "warranty": "25-Year"}
    },
    {
        "sku": "ENOH-DOUBL-NEST",
        "name": "ENO DoubleNest Portable Camping Hammock",
        "description": "Spacious two-person camping hammock made from breathable 70D High Tenacity taffeta nylon with heavy-duty triple interlocking stitching and wiregate carabiners.",
        "category": "Footwear & Outdoor",
        "price": 74.95,
        "stock": 35,
        "attributes": {"brand": "Eagles Nest Outfitters", "weight_capacity_lbs": 400, "material": "70D Nylon Taffeta", "color": "Navy/Olive"}
    },
    {
        "sku": "BLACK-DIAM-TRAIL-POL",
        "name": "Black Diamond Trail Pro Shock Trekking Poles (Pair)",
        "description": "FlickLock Pro dual-cam adjustment poles with Control Shock Technology in the grip, soft ergonomic foam handles, and interchangeable carbide tech tips.",
        "category": "Footwear & Outdoor",
        "price": 159.95,
        "stock": 20,
        "attributes": {"brand": "Black Diamond", "shock_absorption": True, "lock": "FlickLock Pro", "material": "Aluminum"}
    },
    {
        "sku": "YETI-TUNDRA-45-TAN",
        "name": "YETI Tundra 45 Hard Heavy-Duty Cooler Desert Tan",
        "description": "Rotomolded construction with up to 3 inches of PermaFrost pressure-injected polyurethane insulation, T-Rex lid latches, and certified bear-resistant design.",
        "category": "Footwear & Outdoor",
        "price": 325.00,
        "stock": 12,
        "attributes": {"brand": "YETI", "capacity_cans": 28, "construction": "Rotomolded", "color": "Desert Tan"}
    },
    {
        "sku": "SEA-SUMMIT-XSET31",
        "name": "Sea to Summit X-Set 31 Collapsible Silicone Cookset",
        "description": "5-piece nesting camping cookset with 2.8L hard-anodized aluminum base silicone kettle/pot, two X-Bowls, and two X-Mugs that collapse down to 1.5 inches flat.",
        "category": "Footwear & Outdoor",
        "price": 129.95,
        "stock": 18,
        "attributes": {"brand": "Sea to Summit", "collapsible": True, "pieces": 5, "material": "Food-grade Silicone / Aluminum"}
    },
    {
        "sku": "PETZ-GRIGRI-PLUS",
        "name": "Petzl GRIGRI + Assisted Braking Belay Device",
        "description": "Assisted braking belay device with anti-panic handle designed for lead and top-rope climbing in gyms or outdoors, compatible with 8.5 to 11mm single ropes.",
        "category": "Footwear & Outdoor",
        "price": 159.95,
        "stock": 15,
        "attributes": {"brand": "Petzl", "type": "Assisted Braking", "rope_diam_mm": "8.5-11", "anti_panic": True}
    },
    {
        "sku": "STAN-CLASS-14QT",
        "name": "Stanley Classic Legendary 1.5 Qt Vacuum Insulated Bottle",
        "description": "Durable rust-proof 18/8 stainless steel thermal bottle keeps coffee hot or iced tea cold for 40 hours, leakproof stopper doubles as 8oz cup.",
        "category": "Footwear & Outdoor",
        "price": 45.00,
        "stock": 40,
        "attributes": {"brand": "Stanley", "capacity_qt": 1.5, "thermal_hours_hot": 40, "color": "Hammertone Green"}
    },
    {
        "sku": "COLO-RIDGE-24-PACK",
        "name": "Gregory Citro 24 H2O Hydration Daypack with 3L Reservoir",
        "description": "Ventilated VaporSpan suspension daypack with included 3D Hydro 3-liter quick-dry reservoir, magnetic drylock bite valve, and trekking pole attachments.",
        "category": "Footwear & Outdoor",
        "price": 149.95,
        "stock": 20,
        "attributes": {"brand": "Gregory", "capacity_liters": 24, "reservoir_liters": 3.0, "suspension": "VaporSpan"}
    },
    {
        "sku": "BIG-AGNES-COP-HV2",
        "name": "Big Agnes Copper Spur HV UL2 Ultralight Tent (Olive)",
        "description": "Award-winning high-volume freestanding 2-person tent with awning-style vestibules, proprietary double ripstop nylon, and TipLok tent buckles.",
        "category": "Footwear & Outdoor",
        "price": 499.95,
        "stock": 8,
        "attributes": {"brand": "Big Agnes", "capacity": "2-Person", "trail_weight_lbs": 2.68, "vestibule": "Awning-Style"}
    },
    {
        "sku": "HELINOX-CHAIR-ZERO",
        "name": "Helinox Chair Zero Ultralight Folding Camp Chair",
        "description": "Weighs only 1.1 pounds and packs smaller than a water bottle, supports up to 265 lbs using DAC proprietary aluminum alloy frame and ripstop polyester seat.",
        "category": "Footwear & Outdoor",
        "price": 149.95,
        "stock": 24,
        "attributes": {"brand": "Helinox", "weight_lbs": 1.1, "capacity_lbs": 265, "frame": "DAC Aluminum"}
    },

    # ==========================================
    # DOMAIN 5: OFFICE & ERGONOMICS FURNITURE (28)
    # ==========================================
    {
        "sku": "HERM-AER-CHAIR",
        "name": "Herman Miller Aeron Ergonomic Mesh Chair",
        "description": "Iconic high-performance ergonomic task chair with breathable Pellicle mesh, PostureFit SL adjustable spinal support, and fully adjustable tilt & arms.",
        "category": "Office & Furniture",
        "price": 1195.00,
        "stock": 8,
        "attributes": {"brand": "Herman Miller", "material": "8Z Pellicle Mesh", "ergonomic": True, "size": "B", "color": "Graphite"}
    },
    {
        "sku": "FLEX-E7-DESK",
        "name": "FlexiSpot E7 Pro Dual-Motor Standing Desk",
        "description": "Heavy-duty motorized height adjustable sit-stand desk with solid bamboo desktop, dual motors, anti-collision system, and 4 memory presets.",
        "category": "Office & Furniture",
        "price": 499.00,
        "stock": 20,
        "attributes": {"motor": "Dual", "desktop": "Solid Bamboo", "weight_capacity_lbs": 355, "dimensions": "55x28 in"}
    },
    {
        "sku": "STLC-GEST-CHAIR",
        "name": "Steelcase Gesture Ergonomic Executive Office Chair",
        "description": "Engineered for computer, tablet, and smartphone postures with Core Equalizer lumbar support, 360-degree rotating arms, and flexible seat perimeter.",
        "category": "Office & Furniture",
        "price": 1399.00,
        "stock": 6,
        "attributes": {"brand": "Steelcase", "arms": "360-degree 4D", "lumbar": "Core Equalizer", "color": "Licorice Fabric"}
    },
    {
        "sku": "UPLIFT-V2-COMM-72",
        "name": "UPLIFT V2 Commercial Solid Walnut Standing Desk 72x30",
        "description": "Premium 1.75-inch thick genuine solid American walnut standing desk with commercial 3-stage crossbar frame, dual motors, and digital memory keypad.",
        "category": "Office & Furniture",
        "price": 1299.00,
        "stock": 5,
        "attributes": {"brand": "UPLIFT", "desktop": "Genuine Solid Walnut", "dimensions": "72x30 in", "weight_capacity_lbs": 355}
    },
    {
        "sku": "HERM-EMBODY-CHAIR",
        "name": "Herman Miller Embody Ergonomic Office Chair",
        "description": "Created with over 30 physicians and biomechanists, featuring Pixelated Support matrix that conforms to micro-movements to reduce pressure buildup.",
        "category": "Office & Furniture",
        "price": 1795.00,
        "stock": 5,
        "attributes": {"brand": "Herman Miller", "support": "Pixelated Matrix", "fabric": "Sync Black", "warranty": "12-Year"}
    },
    {
        "sku": "GROV-WOOD-DESK-SHELF",
        "name": "Grovemade Solid Hardwood Desk Shelf Monitor Stand",
        "description": "Architectural desk riser handcrafted from solid American walnut, natural cork feet, and 5052 aluminum shelf for organizing keyboard and notebook.",
        "category": "Office & Furniture",
        "price": 280.00,
        "stock": 18,
        "attributes": {"brand": "Grovemade", "wood": "American Walnut", "material": "Solid Wood & Aluminum", "length_inches": 46}
    },
    {
        "sku": "ERGO-LX-MON-ARM",
        "name": "Ergotron LX Desk Mount Single Monitor Arm (Polished Aluminum)",
        "description": "Patented Constant Force lift and pivot technology allows effortless fingertip positioning of screens up to 34 inches and 25 lbs with cable management.",
        "category": "Office & Furniture",
        "price": 189.95,
        "stock": 25,
        "attributes": {"brand": "Ergotron", "max_screen_size": "34 inch", "max_weight_lbs": 25, "mount": "Desk Clamp / Grommet"}
    },
    {
        "sku": "VARI-DESK-PRO-PLUS36",
        "name": "VariDesk Pro Plus 36 Height-Adjustable Desk Converter",
        "description": "Dual-tier sit-stand converter with spring-assisted lift mechanism, 11 height settings, and spacious upper display tier with lower keyboard/mouse deck.",
        "category": "Office & Furniture",
        "price": 395.00,
        "stock": 14,
        "attributes": {"brand": "Vari", "width_inches": 36, "mechanism": "Dual-Handle Spring", "tiers": 2}
    },
    {
        "sku": "TOPOG-ANTI-FATIG-MAT",
        "name": "Topo by Ergodriven Calculated Standing Desk Mat",
        "description": "Ergonomically engineered anti-fatigue standing desk mat with calculated terrain contours that encourage subconscious movement, calf raises, and stretches.",
        "category": "Office & Furniture",
        "price": 99.00,
        "stock": 35,
        "attributes": {"brand": "Ergodriven", "terrain": "Next-Gen Topographic", "material": "100% Polyurethane", "color": "Obsidian Black"}
    },
    {
        "sku": "STEEL-LEAP-V2-FAB",
        "name": "Steelcase Leap V2 Ergonomic Task Chair",
        "description": "LiveBack technology changes shape to mimic spine movement, Natural Glide system allows reclining while keeping you aligned with desk and work.",
        "category": "Office & Furniture",
        "price": 1099.00,
        "stock": 10,
        "attributes": {"brand": "Steelcase", "technology": "LiveBack", "weight_capacity_lbs": 400, "color": "Buzz2 Black"}
    },
    {
        "sku": "DYSO-SOLAR-TASK-LGT",
        "name": "Dyson Solarcycle Morph Smart Desk Task Light",
        "description": "Intelligent daylight tracking adjusts color temperature and brightness in real time with 3-Point Revolute motion to convert from task to ambient lamp.",
        "category": "Office & Furniture",
        "price": 649.99,
        "stock": 8,
        "attributes": {"brand": "Dyson", "led_life_years": 60, "tracking": "Local Daylight Tracking", "color": "Black"}
    },
    {
        "sku": "FELL-FOOTREST-PRO",
        "name": "Fellowes Climate Control Climate-Active Ergonomic Footrest",
        "description": "Adjustable footrest with built-in fan and ceramic heater settings to personalize under-desk climate, massaging textured bumps, and 3 tilt angle levels.",
        "category": "Office & Furniture",
        "price": 89.99,
        "stock": 28,
        "attributes": {"brand": "Fellowes", "features": "Heated & Fan Climate Control", "tilt_angles": 3}
    },
    {
        "sku": "HAG-CAPISCO-8106",
        "name": "HÅG Capisco 8106 Ergonomic Saddle Task Chair",
        "description": "Saddle seat chair designed for active sitting, allows sitting forward, backward, or sideways, perfect for switching between sitting and semi-standing desks.",
        "category": "Office & Furniture",
        "price": 995.00,
        "stock": 7,
        "attributes": {"brand": "HÅG", "style": "Saddle Chair", "active_sitting": True, "color": "Select Black Wool"}
    },
    {
        "sku": "SANUS-DUAL-MON-ARM",
        "name": "SANUS Premium Dual Heavy-Duty Monitor Mount Arm",
        "description": "Full-motion gas spring dual monitor mount for side-by-side screens up to 32 inches, integrated cable routing channels, and quick-release VESA plates.",
        "category": "Office & Furniture",
        "price": 149.99,
        "stock": 20,
        "attributes": {"brand": "SANUS", "arms": "Dual Gas Spring", "screen_support": "Up to 32 in each", "vesa": "75x75 / 100x100"}
    },
    {
        "sku": "GROV-WOOL-FELT-PAD",
        "name": "Grovemade Extra Large German Merino Wool Felt Desk Pad",
        "description": "Natural 3mm thick German merino wool felt desk pad offering a warm, soft cushioned surface for keyboard, mouse, wrists, and desk aesthetics.",
        "category": "Office & Furniture",
        "price": 80.00,
        "stock": 30,
        "attributes": {"brand": "Grovemade", "material": "100% German Merino Wool", "size": "XL (38x16 in)", "color": "Dark Heather Grey"}
    },
    {
        "sku": "HON-IGNITION-2-MESH",
        "name": "HON Ignition 2.0 Mid-Back Ergonomic Mesh Task Chair",
        "description": "Breathable 4-way stretch mesh back with adjustable lumbar cradle, synchro-tilt mechanism, pneumatic seat height adjustment, and 300 lb weight rating.",
        "category": "Office & Furniture",
        "price": 389.00,
        "stock": 22,
        "attributes": {"brand": "HON", "weight_capacity_lbs": 300, "lumbar": "Adjustable", "tilt": "Synchro-Tilt"}
    },
    {
        "sku": "HUMAN-QUICK-STAND",
        "name": "Humanscale QuickStand Eco Sit-Stand Tabletop Workstation",
        "description": "Minimalist countertop sit-stand system with smooth counterbalanced height mechanism, integrated cable management, and compact footprint.",
        "category": "Office & Furniture",
        "price": 499.00,
        "stock": 9,
        "attributes": {"brand": "Humanscale", "material": "Sustainable Aluminum/POM", "screen_mount": "Single VESA"}
    },
    {
        "sku": "ANKR-SOLIX-DESK-PS",
        "name": "Anker SOLIX 6-in-1 Under-Desk Cable Management Power Strip",
        "description": "Heavy-duty surge protector with 3 AC outlets, 2 USB-C 65W PD ports, 1 USB-A port, clamps directly to the back edge of desks with zero drilling.",
        "category": "Office & Furniture",
        "price": 59.99,
        "stock": 45,
        "attributes": {"brand": "Anker", "mounting": "Edge Clamp", "pd_wattage": 65, "outlets": 3}
    },
    {
        "sku": "POPPIN-3DRAWER-CAB",
        "name": "Poppin Stow 3-Drawer Locking Steel Rolling File Cabinet",
        "description": "Sleek powder-coated steel mobile pedestal file cabinet with lockable drawers, smooth casters, and hanging file frame for Letter or Legal size files.",
        "category": "Office & Furniture",
        "price": 279.00,
        "stock": 12,
        "attributes": {"brand": "Poppin", "material": "Powder-Coated Steel", "lockable": True, "color": "Charcoal"}
    },
    {
        "sku": "OAKY-DUAL-VERT-STD",
        "name": "Oakywood Dual Solid Oak Vertical Laptop Stand",
        "description": "Handcrafted double vertical laptop dock made of solid FSC-certified Polish oak wood with adjustable felt-lined slots to organize two MacBooks or iPads.",
        "category": "Office & Furniture",
        "price": 79.00,
        "stock": 25,
        "attributes": {"brand": "Oakywood", "material": "Solid Oak Wood", "slots": 2, "finish": "Natural Eco-Oil"}
    },
    {
        "sku": "BLUE-AIR-PURE-411",
        "name": "Blueair Blue Pure 411i Max Quiet Desktop Air Purifier",
        "description": "HEPASilent dual filtration cleans 219 sq ft in 12.5 minutes, whisper-quiet 18dB operation, air quality indicator light, and smart WiFi app control.",
        "category": "Office & Furniture",
        "price": 169.99,
        "stock": 30,
        "attributes": {"brand": "Blueair", "sq_ft_coverage": 219, "noise_db": 18, "filtration": "HEPASilent"}
    },
    {
        "sku": "HERM-SAYL-CHAIR",
        "name": "Herman Miller Sayl Frameless Ergonomic Desk Chair",
        "description": "Yves Béhar suspension bridge inspired 3D Intelligent elastomer back provides dynamic ergonomic support with small environmental footprint.",
        "category": "Office & Furniture",
        "price": 795.00,
        "stock": 11,
        "attributes": {"brand": "Herman Miller", "designer": "Yves Béhar", "back": "3D Intelligent Elastomer", "color": "Studio White/Fog"}
    },
    {
        "sku": "JABR-SPEAK-750",
        "name": "Jabra Speak 750 Premium Wireless Conference Speakerphone",
        "description": "Full duplex audio speakerphone with omnidirectional microphone, dedicated Microsoft Teams button, crystal-clear acoustic echo cancellation.",
        "category": "Office & Furniture",
        "price": 289.00,
        "stock": 16,
        "attributes": {"brand": "Jabra", "audio": "Full Duplex", "teams_certified": True, "battery_hours": 11}
    },
    {
        "sku": "NEAT-DESK-ORGAN-WAL",
        "name": "NeatDesk Solid Walnut Modular Desk Organizer Tray Set",
        "description": "5-piece modular magnetic desk organizer trays crafted from dark walnut wood with hidden magnets to configure pen holders, sticky notes, and phone docks.",
        "category": "Office & Furniture",
        "price": 64.00,
        "stock": 35,
        "attributes": {"material": "Solid Walnut", "pieces": 5, "magnetic": True}
    },
    {
        "sku": "FELL-ELEV-REST-WRIST",
        "name": "Fellowes PlushTouch Foam Keyboard & Mouse Wrist Rest Set",
        "description": "Memory foam wrist rest pair with Microban antimicrobial protection and non-skid backing to relieve pressure points during extended typing sessions.",
        "category": "Office & Furniture",
        "price": 32.99,
        "stock": 50,
        "attributes": {"brand": "Fellowes", "material": "Memory Foam / Microban", "pieces": 2}
    },
    {
        "sku": "KVMS-PRO-4K-SWITCH",
        "name": "AV Access 2-Port 4K@60Hz Dual Monitor KVM Switch",
        "description": "Seamlessly switch 2 computers between 2 monitors and 4 USB 3.0 peripherals with hotkey switching, EDID emulation, and zero latency.",
        "category": "Office & Furniture",
        "price": 149.99,
        "stock": 15,
        "attributes": {"ports": "2 In 2 Out", "resolution": "4K@60Hz", "usb": "USB 3.0 Hub"}
    },
    {
        "sku": "STEEL-SERIES-QCK-PR",
        "name": "Steelcase High-Density Wool Privacy Desk Divider 60x18",
        "description": "Acoustic sound-absorbing PET recycled felt desk clamp divider panel provides visual privacy and dampens ambient speech noise in open workspaces.",
        "category": "Office & Furniture",
        "price": 175.00,
        "stock": 14,
        "attributes": {"brand": "Steelcase", "material": "Acoustic PET Felt", "dimensions": "60x18 in", "clamp_on": True}
    },
    {
        "sku": "BAMB-BALANCE-BRD",
        "name": "FluidStance The Level Solid Bamboo Standing Balance Board",
        "description": "Precision die-cast aluminum base and solid bamboo top deck creates subtle 360-degree micro-movements to increase heart rate and energy while standing.",
        "category": "Office & Furniture",
        "price": 189.00,
        "stock": 12,
        "attributes": {"brand": "FluidStance", "material": "Solid Bamboo & Aluminum", "weight_capacity_lbs": 300}
    },

    # ==========================================
    # DOMAIN 6: KITCHEN, DINING & COFFEE GEAR (30)
    # ==========================================
    {
        "sku": "CHEMEX-OTT-6C",
        "name": "Chemex Classic Eight-Cup Pour-Over Glass Coffeemaker",
        "description": "Classic hourglass pour-over brewer made of non-porous borosilicate glass with polished wood collar and leather tie. Produces pure, sediment-free coffee.",
        "category": "Kitchen & Home",
        "price": 48.95,
        "stock": 40,
        "attributes": {"material": "Borosilicate Glass", "capacity_cups": 8, "brand": "Chemex"}
    },
    {
        "sku": "FELL-STAG-EKG",
        "name": "Fellow Stagg EKG Electric Gooseneck Kettle",
        "description": "Precision pour-over electric kettle with variable temperature control, LCD screen, 60-minute temperature hold, and sleek matte black minimalist aesthetic.",
        "category": "Kitchen & Home",
        "price": 165.00,
        "stock": 22,
        "attributes": {"color": "Matte Black", "capacity_liters": 0.9, "temp_control": True}
    },
    {
        "sku": "BREV-BAR-TOUCH",
        "name": "Breville the Barista Touch Espresso Machine (Brushed Steel)",
        "description": "Automated touchscreen espresso machine with integrated precision conical burr grinder, ThermoJet 3-second heat up, and automatic microfoam milk texturing.",
        "category": "Kitchen & Home",
        "price": 999.95,
        "stock": 7,
        "attributes": {"brand": "Breville", "grinder": "Integrated Conical Burr", "display": "Color Touchscreen", "material": "Stainless Steel"}
    },
    {
        "sku": "FELL-ODE-GEN2",
        "name": "Fellow Ode Gen 2 Precision Home Coffee Grinder",
        "description": "Dedicated home filter coffee burr grinder with 64mm professional flat burrs, new anti-static ionizer, 31 grind settings, and auto-stop technology.",
        "category": "Kitchen & Home",
        "price": 345.00,
        "stock": 14,
        "attributes": {"brand": "Fellow", "burr_size_mm": 64, "burr_type": "Flat Stainless Steel", "anti_static": True}
    },
    {
        "sku": "LECR-RND-DO-55",
        "name": "Le Creuset Enameled Cast Iron Round Dutch Oven 5.5 Qt (Cerise)",
        "description": "Heirloom French enameled cast iron Dutch oven providing superior heat distribution and moisture retention with composite heat-resistant knob.",
        "category": "Kitchen & Home",
        "price": 420.00,
        "stock": 12,
        "attributes": {"brand": "Le Creuset", "capacity_qt": 5.5, "material": "Enameled Cast Iron", "color": "Cerise Red", "made_in": "France"}
    },
    {
        "sku": "VITAM-A3500-ASC",
        "name": "Vitamix Ascent Series A3500 Smart Professional Blender",
        "description": "Commercial-grade 2.2 peak HP motor with 5 program presets, touchscreen controls, built-in wireless timer, and Self-Detect container technology.",
        "category": "Kitchen & Home",
        "price": 649.95,
        "stock": 10,
        "attributes": {"brand": "Vitamix", "horsepower": 2.2, "presets": 5, "container_oz": 64, "warranty": "10-Year"}
    },
    {
        "sku": "WUST-CLAS-CHEF-8",
        "name": "Wüsthof Classic 8-Inch Forged Chef's Knife (Solingen)",
        "description": "Precision forged from a single piece of high-carbon stain-free stainless steel in Solingen, Germany, with 58 HRC Rockwell hardness and triple-rivet handle.",
        "category": "Kitchen & Home",
        "price": 170.00,
        "stock": 25,
        "attributes": {"brand": "Wüsthof", "blade_length_inches": 8, "steel": "X50CrMoV15", "hardness_hrc": 58, "made_in": "Germany"}
    },
    {
        "sku": "LODGE-CAST-12IN",
        "name": "Lodge 12-Inch Pre-Seasoned Cast Iron Skillet with Silicone Handle",
        "description": "Essential American-made cast iron skillet pre-seasoned with 100% natural vegetable oil for searing, baking, broiling, frying, or campfires.",
        "category": "Kitchen & Home",
        "price": 34.90,
        "stock": 60,
        "attributes": {"brand": "Lodge", "diameter_inches": 12, "material": "Pre-Seasoned Cast Iron", "made_in": "USA"}
    },
    {
        "sku": "AEROP-ORIG-BREW",
        "name": "AeroPress Original Coffee and Espresso Style Maker",
        "description": "Rapid total immersion brewing creates smooth, rich, grit-free coffee in under a minute with zero bitterness and 1/9th the acidity of French press.",
        "category": "Kitchen & Home",
        "price": 39.95,
        "stock": 70,
        "attributes": {"brand": "AeroPress", "brew_time_sec": 60, "portable": True, "bpa_free": True}
    },
    {
        "sku": "NINJA-AIRFRY-8QT",
        "name": "Ninja Foodi 8-Qt DualZone 2-Basket Air Fryer with Smart Cook",
        "description": "2 independent nonstick baskets to cook 2 foods 2 ways simultaneously with Smart Finish sync, 6 customizable functions, and up to 450F heat.",
        "category": "Kitchen & Home",
        "price": 199.99,
        "stock": 20,
        "attributes": {"brand": "Ninja", "capacity_qt": 8, "baskets": 2, "functions": "Air Fry, Roast, Broil, Bake, Reheat, Dehydrate"}
    },
    {
        "sku": "ALLCL-D3-10P-SET",
        "name": "All-Clad D3 Tri-Ply Stainless Steel 10-Piece Cookware Set",
        "description": "Classic tri-ply bonded construction with responsive aluminum core bonded between two layers of 18/10 stainless steel for even heat edge-to-edge.",
        "category": "Kitchen & Home",
        "price": 799.95,
        "stock": 6,
        "attributes": {"brand": "All-Clad", "pieces": 10, "ply": "Tri-Ply D3 Stainless", "induction_compatible": True, "made_in": "USA"}
    },
    {
        "sku": "CUIS-FP-14-PROC",
        "name": "Cuisinart Custom 14-Cup Large Food Processor Stainless",
        "description": "Heavy-duty 720-watt motor handles dough, slicing, shredding, chopping, and pureeing with extra-large feed tube and stainless steel blades.",
        "category": "Kitchen & Home",
        "price": 249.95,
        "stock": 15,
        "attributes": {"brand": "Cuisinart", "capacity_cups": 14, "motor_watts": 720, "bowl_bpa_free": True}
    },
    {
        "sku": "BREV-SMART-OVEN-AIR",
        "name": "Breville Smart Oven Air Fryer Pro Countertop Convection",
        "description": "Super Convection with Element iQ technology provides 13 cooking functions, fits a 14 lb turkey or 9x13 inch pan, dual-speed fan.",
        "category": "Kitchen & Home",
        "price": 399.95,
        "stock": 10,
        "attributes": {"brand": "Breville", "functions_count": 13, "element_iq": True, "capacity_cu_ft": 1.0}
    },
    {
        "sku": "HARIO-V60-02-CER",
        "name": "Hario V60 Ceramic Coffee Dripper Size 02 (White Arita-yaki)",
        "description": "Japanese ceramic pour-over cone with 60-degree angle, spiral ribs, and single large exit hole for complete control over brew flow rate.",
        "category": "Kitchen & Home",
        "price": 27.50,
        "stock": 55,
        "attributes": {"brand": "Hario", "material": "Arita Ceramic", "size": "02 (1-4 Cups)", "made_in": "Japan"}
    },
    {
        "sku": "SHUN-CLAS-SANTO-7",
        "name": "Shun Classic 7-Inch Damascus Steel Santoku Knife",
        "description": "Handcrafted in Seki, Japan with proprietary VG-MAX cutting core clad with 68 micro-layers of Damascus steel and D-shaped Pakkawood handle.",
        "category": "Kitchen & Home",
        "price": 169.95,
        "stock": 18,
        "attributes": {"brand": "Shun", "blade_type": "Santoku", "steel": "VG-MAX Damascus", "made_in": "Japan"}
    },
    {
        "sku": "INST-POT-PRO-PLUS",
        "name": "Instant Pot Pro Plus Smart 10-in-1 WiFi Pressure Cooker 6 Qt",
        "description": "Smart multi-cooker with app control, gentle steam release, NutriBoost pulse technology, 20% faster preheating, and 10 cooking functions.",
        "category": "Kitchen & Home",
        "price": 169.99,
        "stock": 25,
        "attributes": {"brand": "Instant Pot", "capacity_qt": 6, "smart_app": True, "functions": 10}
    },
    {
        "sku": "ZORJ-MICOM-RICE-55",
        "name": "Zojirushi Neuro Fuzzy 5.5-Cup Micom Rice Cooker & Warmer",
        "description": "Advanced Neuro Fuzzy logic technology monitors heating temperatures to cook flawless white, sushi, brown, and porridge rice with spherical inner pan.",
        "category": "Kitchen & Home",
        "price": 234.00,
        "stock": 16,
        "attributes": {"brand": "Zojirushi", "capacity_cups": 5.5, "technology": "Neuro Fuzzy Logic", "made_in": "Japan"}
    },
    {
        "sku": "OXO-BREW-9CUP-MAKER",
        "name": "OXO Brew 9-Cup Stainless Steel Coffee Maker (SCA Certified)",
        "description": "Specialty Coffee Association (SCA) certified automated drip maker with microprocessor-controlled brew cycle, Rainmaker showerhead, and thermal carafe.",
        "category": "Kitchen & Home",
        "price": 229.95,
        "stock": 14,
        "attributes": {"brand": "OXO", "sca_certified": True, "carafe": "Double-Wall Thermal", "capacity_cups": 9}
    },
    {
        "sku": "STAUB-COCOTTE-4QT",
        "name": "Staub Cast Iron Round Cocotte 4-Qt (Matte Black)",
        "description": "Enameled cast iron cocotte with spiked flat Chistera drop-structure lid for continuous self-basting, rough matte black interior for superior searing.",
        "category": "Kitchen & Home",
        "price": 319.99,
        "stock": 12,
        "attributes": {"brand": "Staub", "capacity_qt": 4.0, "material": "Enameled Cast Iron", "made_in": "France"}
    },
    {
        "sku": "ANVA-PREC-SOUS-VID",
        "name": "Anova Precision Cooker 3.0 WiFi Sous Vide Immersion Circulator",
        "description": "1100-watt immersion circulator accurate to +/- 0.1C, WiFi connected with guided app recipes, clamps easily to any stock pot for restaurant-quality meats.",
        "category": "Kitchen & Home",
        "price": 199.00,
        "stock": 20,
        "attributes": {"brand": "Anova", "wattage": 1100, "accuracy_c": 0.1, "connectivity": "WiFi & Bluetooth"}
    },
    {
        "sku": "THERMAPEN-ONE-THRM",
        "name": "ThermoWorks Thermapen ONE 1-Second Instant-Read Meat Thermometer",
        "description": "Industry benchmark culinary thermometer with full 1-second temperature readings accurate to +/- 0.5F, auto-rotating backlit display, and IP67 waterproof body.",
        "category": "Kitchen & Home",
        "price": 105.00,
        "stock": 45,
        "attributes": {"brand": "ThermoWorks", "read_time_sec": 1.0, "accuracy_f": 0.5, "waterproof": "IP67"}
    },
    {
        "sku": "EMBR-MUG2-14OZ",
        "name": "Ember Temperature Control Smart Mug 2 (14 oz, Matte Black)",
        "description": "App-controlled heated ceramic mug maintains exact drinking temperature between 120F and 145F for 80 minutes on a single charge or all day on charging coaster.",
        "category": "Kitchen & Home",
        "price": 149.95,
        "stock": 30,
        "attributes": {"brand": "Ember", "capacity_oz": 14, "battery_minutes": 80, "color": "Matte Black"}
    },
    {
        "sku": "BOOS-BLCK-CHOP-MAP",
        "name": "John Boos Block Maple Wood End-Grain Reversible Chopping Block 20x15",
        "description": "2.25-inch thick solid Northern hard rock maple end-grain butcher block with integrated finger grips, NSF certified, treated with natural beeswax finish.",
        "category": "Kitchen & Home",
        "price": 220.00,
        "stock": 10,
        "attributes": {"brand": "John Boos", "wood": "Hard Rock Maple", "construction": "End-Grain", "thickness_in": 2.25}
    },
    {
        "sku": "ACAI-LUN-PREC-SCL",
        "name": "Acaia Lunar Precision Waterproof Espresso Scale",
        "description": "Ultra-precise 0.01g water-resistant espresso scale crafted from premium anodized aluminum with built-in auto-tare and auto-start flow-rate timers.",
        "category": "Kitchen & Home",
        "price": 250.00,
        "stock": 15,
        "attributes": {"brand": "Acaia", "precision_g": 0.01, "water_resistant": True, "connectivity": "Bluetooth App"}
    },
    {
        "sku": "MICRO-PREM-ZEST",
        "name": "Microplane Premium Classic Stainless Steel Zester Grater",
        "description": "Surgical-grade photo-etched stainless steel blades for zesting citrus, grating hard parmesan cheese, ginger, garlic, and nutmeg with ergonomic handle.",
        "category": "Kitchen & Home",
        "price": 17.99,
        "stock": 80,
        "attributes": {"brand": "Microplane", "material": "Surgical Stainless Steel", "color": "Classic Black"}
    },
    {
        "sku": "SODAST-TERRA-SPK",
        "name": "SodaStream Terra Sparkling Water Maker Bundle with CO2",
        "description": "Cordless carbonating machine with Quick Connect CO2 cylinder technology, includes 2 dishwasher-safe 1L reusable BPA-free bottles.",
        "category": "Kitchen & Home",
        "price": 89.99,
        "stock": 25,
        "attributes": {"brand": "SodaStream", "bottles_included": 2, "cordless": True, "color": "Matte White"}
    },
    {
        "sku": "KITCH-ART-5QT-MIX",
        "name": "KitchenAid Artisan Series 5-Quart Tilt-Head Stand Mixer",
        "description": "Iconic stand mixer with 10 speeds, 59-point planetary mixing action, 5-quart stainless steel bowl with handle, includes flat beater, dough hook, and wire whip.",
        "category": "Kitchen & Home",
        "price": 449.99,
        "stock": 12,
        "attributes": {"brand": "KitchenAid", "capacity_qt": 5.0, "speeds": 10, "color": "Empire Red"}
    },
    {
        "sku": "OXO-GOOD-SAL-SPN",
        "name": "OXO Good Grips Large Stainless Steel Salad Spinner",
        "description": "One-handed pump mechanism with patented brake button, non-slip base, clear lid, and elegant stainless steel bowl that doubles as a serving dish.",
        "category": "Kitchen & Home",
        "price": 64.95,
        "stock": 35,
        "attributes": {"brand": "OXO", "material": "Stainless Steel / Tritan", "one_handed": True}
    },
    {
        "sku": "DEAL-NONST-FRY-10",
        "name": "Made In Cookware 10-Inch Non Stick Frying Pan (PFOA-Free)",
        "description": "5-ply American stainless clad construction with dual-layer premium non-stick coating engineered to last 10x longer, oven safe up to 500F.",
        "category": "Kitchen & Home",
        "price": 129.00,
        "stock": 24,
        "attributes": {"brand": "Made In", "ply": "5-Ply Clad", "pfoa_free": True, "size_inches": 10}
    },
    {
        "sku": "CUIS-GR-4N-GRIDD",
        "name": "Cuisinart 5-in-1 Griddler Contact Grill & Panini Press",
        "description": "Reversible nonstick cooking plates function as contact grill, full grill, full griddle, half grill/half griddle, and panini press with adjustable temperature.",
        "category": "Kitchen & Home",
        "price": 99.95,
        "stock": 20,
        "attributes": {"brand": "Cuisinart", "functions": 5, "plates": "Reversible Non-Stick", "dishwasher_safe": True}
    },

    # ==========================================
    # DOMAIN 7: SMART HOME & APPLIANCES (28)
    # ==========================================
    {
        "sku": "ROBO-Q-REVO-MAXV",
        "name": "Roborock Q Revo MaxV Robot Vacuum and Mop with AI Obstacle Avoidance",
        "description": "7000Pa extreme suction with dual spinning mops, auto mop lifting, 60C hot water washing auto-emptying dock, and Reactive AI camera navigation.",
        "category": "Smart Home & Appliances",
        "price": 1199.99,
        "stock": 8,
        "attributes": {"brand": "Roborock", "suction_pa": 7000, "dock": "All-in-One Hot Wash", "navigation": "Reactive AI LiDAR"}
    },
    {
        "sku": "NEST-LRN-THERM-3",
        "name": "Google Nest Learning Thermostat 3rd Generation (Polished Steel)",
        "description": "Smart programmable thermostat that learns your schedule, auto-adjusts eco temperatures to save energy, and works with Google Home and Alexa.",
        "category": "Smart Home & Appliances",
        "price": 249.00,
        "stock": 25,
        "attributes": {"brand": "Google Nest", "compatibility": "95% 24V Systems", "energy_star": True, "color": "Polished Steel"}
    },
    {
        "sku": "PHIL-HUE-STRT-KIT",
        "name": "Philips Hue White and Color Ambiance Smart Bulb Starter Kit (4 A19 Bulbs)",
        "description": "16 million colors and tunable white lighting with included Hue Bridge, Zigbee reliable mesh networking, Matter compatible, works with HomeKit/Alexa.",
        "category": "Smart Home & Appliances",
        "price": 199.99,
        "stock": 30,
        "attributes": {"brand": "Philips Hue", "bulbs_count": 4, "protocol": "Zigbee / Matter", "lumens": 1100}
    },
    {
        "sku": "RING-BAT-DOOR-PLUS",
        "name": "Ring Battery Doorbell Plus with Head-to-Toe 1536p HD Video",
        "description": "Wireless video doorbell with expanded head-to-toe field of view, color night vision, motion detection with package alerts, and quick-release battery.",
        "category": "Smart Home & Appliances",
        "price": 179.99,
        "stock": 35,
        "attributes": {"brand": "Ring", "resolution": "1536p HD", "fov": "Head-to-Toe 150x150", "battery": "Rechargeable"}
    },
    {
        "sku": "AUG-WIFI-SMART-LCK",
        "name": "August Wi-Fi Smart Deadbolt Lock (4th Gen) Matte Black",
        "description": "Attaches to your existing deadbolt on the inside of the door, built-in WiFi with no bridge required, auto-unlocks on approach via smartphone geolocation.",
        "category": "Smart Home & Appliances",
        "price": 229.99,
        "stock": 18,
        "attributes": {"brand": "August", "wifi_built_in": True, "retrofit": True, "color": "Matte Black"}
    },
    {
        "sku": "DYSO-PUR-HOT-HP09",
        "name": "Dyson Purifier Hot+Cool Formaldehyde HP09 Air Purifier & Heater",
        "description": "Triple functionality: HEPA H13 air purifier, intelligent space heater, and cooling fan. Destroys formaldehyde permanently with solid-state sensor.",
        "category": "Smart Home & Appliances",
        "price": 749.99,
        "stock": 6,
        "attributes": {"brand": "Dyson", "filtration": "HEPA H13 + Formaldehyde", "heating": True, "cooling": True}
    },
    {
        "sku": "ECOL-SMART-CAM-3PK",
        "name": "Eufy Security eufyCam 3 4K Wireless Camera System (2-Cam Kit)",
        "description": "4K Ultra HD cameras with integrated solar panels for infinite power, BionicMind AI facial recognition, local storage with zero monthly fees.",
        "category": "Smart Home & Appliances",
        "price": 479.99,
        "stock": 12,
        "attributes": {"brand": "Eufy", "resolution": "4K UHD", "power": "Integrated Solar", "monthly_fee": "$0 Local Storage"}
    },
    {
        "sku": "ECOBEE-PREM-THRM",
        "name": "ecobee Smart Thermostat Premium with SmartSensor & Air Quality",
        "description": "Zinc construction with radar occupancy detection, built-in air quality monitor, voice assistant integration, and remote SmartSensor included.",
        "category": "Smart Home & Appliances",
        "price": 249.99,
        "stock": 20,
        "attributes": {"brand": "ecobee", "sensor_included": True, "air_quality_monitor": True, "material": "Brushed Zinc"}
    },
    {
        "sku": "LEVO-CORE-400S-PUR",
        "name": "Levoit Core 400S Smart True HEPA Air Purifier 403 Sq Ft",
        "description": "VortexAir 3.0 technology purifies a 403 sq ft room 5 times per hour, AirSight Plus laser dust sensor, smartphone monitoring, ultra-quiet 24dB Sleep Mode.",
        "category": "Smart Home & Appliances",
        "price": 219.99,
        "stock": 25,
        "attributes": {"brand": "Levoit", "coverage_sq_ft": 403, "hepa": "H13 True HEPA", "smart_app": True}
    },
    {
        "sku": "EERO-MAX-7-MESH",
        "name": "Amazon eero Max 7 Tri-Band Mesh WiFi 7 Router (Single Unit)",
        "description": "Blazing fast WiFi 7 speeds up to 9.4 Gbps, covers up to 2500 sq ft, connects 200+ devices, includes 2x 10GbE and 2x 2.5GbE Ethernet ports.",
        "category": "Smart Home & Appliances",
        "price": 599.99,
        "stock": 10,
        "attributes": {"brand": "eero", "standard": "Wi-Fi 7", "coverage_sq_ft": 2500, "ethernet_ports": "2x 10GbE + 2x 2.5GbE"}
    },
    {
        "sku": "KASA-SMART-PLUG-4P",
        "name": "Kasa Smart Wi-Fi Plug Mini 4-Pack with Energy Monitoring",
        "description": "Compact smart plugs with real-time energy consumption tracking, scheduling, timer countdowns, and voice control via Alexa and Google Assistant.",
        "category": "Smart Home & Appliances",
        "price": 29.99,
        "stock": 60,
        "attributes": {"brand": "TP-Link Kasa", "pack": 4, "energy_monitoring": True, "protocol": "2.4GHz WiFi"}
    },
    {
        "sku": "YALE-ASSURE-LCK2-P",
        "name": "Yale Assure Lock 2 Touch Keyless Smart Deadbolt with Fingerprint",
        "description": "Biometric fingerprint scanner, illuminated keypad, auto-unlock with Bluetooth/WiFi, and physical backup keyway in satin nickel finish.",
        "category": "Smart Home & Appliances",
        "price": 279.99,
        "stock": 15,
        "attributes": {"brand": "Yale", "biometric": "Fingerprint Scanner", "keypad": "Backlit Touch", "color": "Satin Nickel"}
    },
    {
        "sku": "IROB-ROOMBA-J9-P",
        "name": "iRobot Roomba Combo j9+ Self-Emptying & Auto-Fill Robot Vacuum and Mop",
        "description": "D.R.I.V.E. retractable mop keeps rugs completely dry, 100% obstacle recognition avoids pet waste and cords, Clean Base auto-empties for 60 days.",
        "category": "Smart Home & Appliances",
        "price": 999.00,
        "stock": 7,
        "attributes": {"brand": "iRobot", "mop": "Retractable Auto-Lift", "obstacle_avoidance": "PrecisionVision AI"}
    },
    {
        "sku": "SWTC-BOT-BLIND-TLT",
        "name": "SwitchBot Smart Motorized Blind Tilt Solar Automation Kit",
        "description": "Retrofit smart blind motor that automates horizontal wand-tilt blinds with built-in light sensor, timers, and included solar charging panel.",
        "category": "Smart Home & Appliances",
        "price": 69.99,
        "stock": 35,
        "attributes": {"brand": "SwitchBot", "solar_panel": True, "light_sensor": True, "voice_control": True}
    },
    {
        "sku": "MOEN-SMART-WATR-SHT",
        "name": "Flo by Moen Smart Home Whole-House Water Shutoff Valve 1-Inch",
        "description": "Monitors pipe pressure, flow rate, and temperature 24/7 to detect micro-leaks and automatically shuts off municipal water main to prevent catastrophic flood damage.",
        "category": "Smart Home & Appliances",
        "price": 499.00,
        "stock": 10,
        "attributes": {"brand": "Moen", "pipe_size_in": 1.0, "auto_shutoff": True, "leak_detection": "Micro-Leak AI"}
    },
    {
        "sku": "AQUA-M2-HUB-ZIGBEE",
        "name": "Aqara Smart Hub M2 Zigbee 3.0 & Matter Bridge with 360 IR Controller",
        "description": "Smart home automation controller with Ethernet, built-in speaker chime, 360-degree infrared blaster to control air conditioners, and Apple HomeKit support.",
        "category": "Smart Home & Appliances",
        "price": 59.99,
        "stock": 40,
        "attributes": {"brand": "Aqara", "protocol": "Zigbee 3.0 / Matter", "ir_blaster": "360 Degree", "homekit": True}
    },
    {
        "sku": "NANOL-LINES-9PK",
        "name": "Nanoleaf Lines 60-Degree Modular Smart Backlit LED Light Bars (9-Pack)",
        "description": "Customizable geometric ambient light bars with dual-color zones per bar, dynamic music visualizer rhythm sync, and Screen Mirror desktop tech.",
        "category": "Smart Home & Appliances",
        "price": 179.99,
        "stock": 20,
        "attributes": {"brand": "Nanoleaf", "bars_count": 9, "lighting": "RGB Backlit Dual-Zone", "music_sync": True}
    },
    {
        "sku": "GREE-CO2-MON-SMART",
        "name": "Qingping Air Monitor Lite with CO2, PM2.5, PM10, Temp & Humidity",
        "description": "Precision indoor air quality monitor with high-precision NDIR CO2 sensor, laser scattering particle sensor, OLED clear display, and Apple HomeKit support.",
        "category": "Smart Home & Appliances",
        "price": 99.99,
        "stock": 28,
        "attributes": {"brand": "Qingping", "sensors": "CO2, PM2.5, PM10, Temp, Humidity", "homekit": True}
    },
    {
        "sku": "WYZE-CAM-V4-2PK",
        "name": "Wyze Cam v4 2.5K QHD Wired Indoor/Outdoor Security Camera 2-Pack",
        "description": "2.5K QHD resolution with Color Night Vision, built-in LED spotlight, two-way audio, IP65 weatherproofing, and microSD card 24/7 continuous local recording.",
        "category": "Smart Home & Appliances",
        "price": 69.98,
        "stock": 45,
        "attributes": {"brand": "Wyze", "resolution": "2.5K QHD", "pack": 2, "weatherproof": "IP65", "color_night_vision": True}
    },
    {
        "sku": "CHAM-MYQ-GAR-OPEN",
        "name": "Chamberlain myQ Smart Garage Door Control Opener Hub",
        "description": "Smart garage retrofit hub enables real-time open/close status notifications, smartphone app control, and secure in-garage Amazon package delivery.",
        "category": "Smart Home & Appliances",
        "price": 29.98,
        "stock": 50,
        "attributes": {"brand": "myQ", "in_garage_delivery": True, "compatibility": "Universal Sensor"}
    },
    {
        "sku": "ECOL-ROBOT-LAWN-MOW",
        "name": "ECOVACS GOAT G1 Wire-Free Robot Lawn Mower",
        "description": "Beacon navigation robot mower eliminating perimeter wire digging, dual fisheye cameras with 3D obstacle avoidance, covers up to 17,000 sq ft.",
        "category": "Smart Home & Appliances",
        "price": 1499.00,
        "stock": 4,
        "attributes": {"brand": "ECOVACS", "wire_free": True, "coverage_sq_ft": 17000, "camera": "Dual 3D Fisheye"}
    },
    {
        "sku": "SENSI-SMART-THRM",
        "name": "Emerson Sensi Touch Smart Thermostat with Color Touchscreen",
        "description": "Easy DIY installation smart thermostat with color touchscreen display, 7-day flexible scheduling, geofencing, and smart home platform integration.",
        "category": "Smart Home & Appliances",
        "price": 149.00,
        "stock": 22,
        "attributes": {"brand": "Sensi", "display": "Color Touchscreen", "energy_star": True}
    },
    {
        "sku": "PHIL-HUE-PLAY-BAR2",
        "name": "Philips Hue Play White & Color Ambiance Light Bar 2-Pack",
        "description": "Versatile TV and monitor backlighting lamps with table stands and TV mounts included, syncs with PC gaming and movies via Hue Sync app.",
        "category": "Smart Home & Appliances",
        "price": 159.99,
        "stock": 25,
        "attributes": {"brand": "Philips Hue", "pack": 2, "tv_sync": True, "lumens": 500}
    },
    {
        "sku": "LUTR-CASETA-DIM-KIT",
        "name": "Lutron Caséta Smart Dimmer Switch Starter Kit with Pico Remote",
        "description": "Ultra-reliable Clear Connect wireless RF smart in-wall dimmer, requires no neutral wire in most homes, works with LED, incandescent, and halogen bulbs.",
        "category": "Smart Home & Appliances",
        "price": 99.95,
        "stock": 30,
        "attributes": {"brand": "Lutron", "protocol": "Clear Connect RF", "neutral_wire_required": False}
    },
    {
        "sku": "SAMS-SMART-TAG2-4P",
        "name": "Samsung Galaxy SmartTag2 Bluetooth Tracker 4-Pack (Black/White)",
        "description": "IP67 water-resistant item tracker with Ultra-Wideband (UWB) Compass View, Lost Mode NFC messaging, and up to 500-day battery life.",
        "category": "Smart Home & Appliances",
        "price": 99.99,
        "stock": 40,
        "attributes": {"brand": "Samsung", "pack": 4, "uwb": True, "battery_days": 500, "ip_rating": "IP67"}
    },
    {
        "sku": "APPL-AIRTAG-4PK",
        "name": "Apple AirTag 4-Pack Bluetooth Item Finder",
        "description": "Keep track of keys, wallet, luggage, and backpack in the Apple Find My network with Precision Finding powered by the Apple U1 Ultra-Wideband chip.",
        "category": "Smart Home & Appliances",
        "price": 99.00,
        "stock": 55,
        "attributes": {"brand": "Apple", "pack": 4, "chip": "Apple U1 UWB", "network": "Apple Find My"}
    },
    {
        "sku": "GOOG-NEST-CAM-OUT",
        "name": "Google Nest Cam Outdoor/Indoor Battery Security Camera",
        "description": "Wire-free weather-resistant smart security camera with intelligent alerts for people, animals, and vehicles, 1080p HDR video with night vision.",
        "category": "Smart Home & Appliances",
        "price": 179.99,
        "stock": 20,
        "attributes": {"brand": "Google Nest", "battery_operated": True, "resolution": "1080p HDR", "magnetic_mount": True}
    },
    {
        "sku": "ECOL-SMART-DROP-BOX",
        "name": "eufy Security SmartDrop Anti-Theft Delivery Package Drop Box",
        "description": "Heavy-duty cold-rolled carbon steel porch safe with built-in 1080p AI camera, remote courier PIN code unlocking, and automatic locking mechanism.",
        "category": "Smart Home & Appliances",
        "price": 399.99,
        "stock": 5,
        "attributes": {"brand": "Eufy", "material": "Carbon Steel", "camera": "1080p HD", "anti_theft": True}
    },

    # ==========================================
    # DOMAIN 8: FITNESS, SPORTS & WELLNESS (28)
    # ==========================================
    {
        "sku": "BOWF-SELECT-552",
        "name": "Bowflex SelectTech 552 Adjustable Dumbbells (Pair)",
        "description": "Adjustable dumbbell set replaces 15 pairs of weights with an intuitive dial system adjusting from 5 to 52.5 lbs in 2.5 lb increments with durable molding.",
        "category": "Sports & Fitness",
        "price": 429.00,
        "stock": 14,
        "attributes": {"brand": "Bowflex", "weight_range_lbs": "5 to 52.5", "pairs_replaced": 15}
    },
    {
        "sku": "MAND-PRO-YOGA-MAT",
        "name": "Manduka PRO Premium 6mm High-Density Yoga Mat (Black Sage)",
        "description": "Legendary ultra-dense 6mm closed-cell PVC yoga mat engineered for joint protection, grip, and lifetime durability, OEKO-TEX certified.",
        "category": "Sports & Fitness",
        "price": 138.00,
        "stock": 30,
        "attributes": {"brand": "Manduka", "thickness_mm": 6.0, "warranty": "Lifetime", "material": "High-Density Closed-Cell PVC"}
    },
    {
        "sku": "THERA-PRO-5-GUN",
        "name": "Theragun PRO 5th Gen Bluetooth Deep Tissue Massage Gun",
        "description": "Professional percussion therapy device with patented EQ-150 brushless motor, 16mm amplitude, OLED screen with visual guided routines, and 6 attachments.",
        "category": "Sports & Fitness",
        "price": 599.00,
        "stock": 10,
        "attributes": {"brand": "Therabody", "amplitude_mm": 16, "motor": "Brushless EQ-150", "attachments": 6}
    },
    {
        "sku": "HYPR-HYPERVOLT-2P",
        "name": "Hyperice Hypervolt 2 Pro Cordless Percussion Massager",
        "description": "Powerful deep relief massage gun with 5 variable speed dial settings, patented pressure sensor technology, and Bluetooth pairing to Hyperice App.",
        "category": "Sports & Fitness",
        "price": 329.00,
        "stock": 18,
        "attributes": {"brand": "Hyperice", "speeds": 5, "battery_hours": 3, "bluetooth": True}
    },
    {
        "sku": "ROGUE-OHIO-BAR-20K",
        "name": "Rogue Fitness The Ohio Bar 20KG Olympic Barbell (Black Oxide)",
        "description": "Manufactured in Columbus, Ohio with 190,000 PSI tensile strength US steel, snap ring design, bronze bushings, and signature Ohio knurl pattern.",
        "category": "Sports & Fitness",
        "price": 295.00,
        "stock": 12,
        "attributes": {"brand": "Rogue Fitness", "weight_kg": 20, "tensile_psi": 190000, "finish": "Black Oxide", "made_in": "USA"}
    },
    {
        "sku": "CONCPT2-ROWER-PM5",
        "name": "Concept2 RowErg Indoor Rowing Machine with PM5 Performance Monitor",
        "description": "Gold standard indoor rower with air resistance flywheel, spiral damper, ergonomic 10-degree bend handle, and PM5 monitor with Bluetooth workout tracking.",
        "category": "Sports & Fitness",
        "price": 990.00,
        "stock": 6,
        "attributes": {"brand": "Concept2", "resistance": "Air Flywheel", "monitor": "PM5", "weight_capacity_lbs": 500}
    },
    {
        "sku": "TRX-PRO4-SUSP-TRN",
        "name": "TRX PRO4 System Suspension Trainer Bodyweight Workout Kit",
        "description": "Commercial-grade suspension trainer with adjustable foot cradles, textured rubber handles, theft-resistant carabiner, and multiple anchor solutions.",
        "category": "Sports & Fitness",
        "price": 249.95,
        "stock": 25,
        "attributes": {"brand": "TRX", "handles": "Textured Rubber", "anchors": "Door & Extender", "weight_capacity_lbs": 350}
    },
    {
        "sku": "WHOOP-40-BAND",
        "name": "WHOOP 4.0 24/7 Continuous Health & Strain Tracker with 12-Mo Membership",
        "description": "Screenless biometric sensor tracking physiological strain, recovery score, sleep stages, skin temperature, and pulse oximetry with SuperKnit band.",
        "category": "Sports & Fitness",
        "price": 239.00,
        "stock": 20,
        "attributes": {"brand": "WHOOP", "sensors": "Heart Rate, Skin Temp, SpO2", "waterproof": "IP68"}
    },
    {
        "sku": "OURA-RING-GEN3-HER",
        "name": "Oura Ring Gen 3 Heritage Smart Ring (Stealth Black)",
        "description": "Ultra-lightweight titanium smart ring tracking sleep stages, daytime heart rate, readiness scores, and early illness indicators with discreet aesthetic.",
        "category": "Sports & Fitness",
        "price": 399.00,
        "stock": 15,
        "attributes": {"brand": "Oura", "material": "Titanium", "finish": "Stealth Black", "battery_days": 7}
    },
    {
        "sku": "IRON-GYM-TOTAL-BAR",
        "name": "Iron Gym Total Upper Body Workout Doorway Pull-Up Bar",
        "description": "Multi-function doorway pull-up bar leverages doorway frame with zero screws or drilling, supports wide, neutral, and close grip pull-ups, push-ups, and dips.",
        "category": "Sports & Fitness",
        "price": 34.99,
        "stock": 45,
        "attributes": {"brand": "Iron Gym", "installation": "No-Drill Doorway", "weight_capacity_lbs": 300}
    },
    {
        "sku": "SPRI-RESIST-BAND-5",
        "name": "SPRI Heavy-Duty Flat Loop Resistance Bands Set of 5",
        "description": "100% natural latex loop exercise bands with 5 color-coded resistance levels from Light (5 lbs) to Ultra Heavy (40 lbs) for glutes, rehab, and warmups.",
        "category": "Sports & Fitness",
        "price": 24.99,
        "stock": 60,
        "attributes": {"brand": "SPRI", "pieces": 5, "material": "Natural Latex", "levels": "X-Light to X-Heavy"}
    },
    {
        "sku": "TRIG-GRID-FOAM-ROL",
        "name": "TriggerPoint GRID 13-Inch Hollow Core EVA Foam Roller (Orange)",
        "description": "Patented multi-density EVA foam surface over a rigid hollow core channels blood and oxygen through muscles to soothe tight knots and speed recovery.",
        "category": "Sports & Fitness",
        "price": 36.95,
        "stock": 40,
        "attributes": {"brand": "TriggerPoint", "length_inches": 13, "core": "Rigid Hollow", "weight_capacity_lbs": 500}
    },
    {
        "sku": "REP-FIT-ADJ-BENCH",
        "name": "REP Fitness AB-3000 2.0 Adjustable Incline Flat Weight Bench",
        "description": "1000-lb rated 11-gauge steel adjustable bench with 8 back positions from flat to 85 degrees, 5 seat positions, and non-slip textured vinyl pad.",
        "category": "Sports & Fitness",
        "price": 319.99,
        "stock": 8,
        "attributes": {"brand": "REP Fitness", "weight_capacity_lbs": 1000, "steel_gauge": 11, "incline_positions": 8}
    },
    {
        "sku": "POLAR-H10-HR-STRAP",
        "name": "Polar H10 Heart Rate Monitor Chest Strap with ECG Precision",
        "description": "The benchmark for accurate ECG heart rate tracking, features dual Bluetooth connections, ANT+ broadcast, internal training memory, and machine-washable strap.",
        "category": "Sports & Fitness",
        "price": 89.95,
        "stock": 35,
        "attributes": {"brand": "Polar", "accuracy": "ECG Gold Standard", "waterproof_m": 30, "connectivity": "Dual Bluetooth + ANT+"}
    },
    {
        "sku": "KETTLE-GRV-24KG-IRN",
        "name": "Rogue Cast Iron Kettlebell 24KG (53 LBS) E-Coat",
        "description": "Single-piece cast iron kettlebell with durable black E-coat finish for superior chalk adhesion, color-coded handle band, and machined flat base.",
        "category": "Sports & Fitness",
        "price": 75.00,
        "stock": 20,
        "attributes": {"brand": "Rogue Fitness", "weight_kg": 24, "finish": "E-Coat", "material": "Ductile Cast Iron"}
    },
    {
        "sku": "SPEED-JUMP-ROPE-PRO",
        "name": "WOD Nation Speed Jump Rope with Dual Ball Bearings",
        "description": "Ultra-fast wire cable speed rope with 360-degree ball bearing swivel in handles for lightning-fast double unders and CrossFit training, includes spare cable.",
        "category": "Sports & Fitness",
        "price": 19.99,
        "stock": 70,
        "attributes": {"brand": "WOD Nation", "bearings": "Dual 360 Ball Bearings", "cable": "Coated Steel Wire"}
    },
    {
        "sku": "CHIRP-WHEEL-3PK-SET",
        "name": "Chirp Wheel+ Back Pain Relief 3-Pack Roller Set",
        "description": "12-inch Gentle, 10-inch Medium, and 6-inch Deep Tissue back stretch wheels with spinal canal groove to protect spine vertebrae while relieving upper and lower back tightness.",
        "category": "Sports & Fitness",
        "price": 99.99,
        "stock": 24,
        "attributes": {"brand": "Chirp", "pieces": 3, "spinal_canal": True, "weight_capacity_lbs": 500}
    },
    {
        "sku": "HYDR-JUG-HALF-GAL",
        "name": "The HydroJug Pro Half Gallon (64 oz) Water Bottle with Straw",
        "description": "BPA-free shatterproof half-gallon water bottle with leakproof dual-function flip cap and integrated silicone straw, measurement markers, and ergonomic handle.",
        "category": "Sports & Fitness",
        "price": 24.99,
        "stock": 50,
        "attributes": {"brand": "HydroJug", "capacity_oz": 64, "material": "BPA-Free Tritan", "color": "Matte Slate"}
    },
    {
        "sku": "BALA-BANG-WEIGHTS",
        "name": "Bala Bangles 1 lb Wearable Ankle and Wrist Weights (Pair, Charcoal)",
        "description": "Chic silicone-wrapped recycled stainless steel weights with ultra-strong elastic Velcro bands for yoga, Pilates, barre, aerobics, and walking workouts.",
        "category": "Sports & Fitness",
        "price": 55.00,
        "stock": 35,
        "attributes": {"brand": "Bala", "weight_lbs_each": 1.0, "material": "Silicone & Stainless Steel", "color": "Charcoal"}
    },
    {
        "sku": "LOCK-JAW-OLY-COLLAR",
        "name": "Lock-Jaw Pro 2 Olympic Barbell Weight Collars (Pair)",
        "description": "Advanced quick-locking resin collar with elastomer pads that clamp solidly onto 2-inch Olympic barbell sleeves to keep plates locked during heavy drops.",
        "category": "Sports & Fitness",
        "price": 39.95,
        "stock": 45,
        "attributes": {"brand": "Lock-Jaw", "barbell_size_in": 2.0, "mechanism": "Cam-Lock Lever"}
    },
    {
        "sku": "YOGA-TOWEL-NONSLIP",
        "name": "Yogitoes by Manduka Skidless Grip Yoga Mat Towel",
        "description": "Microfiber yoga towel with patented silicone dot Skidless technology on bottom to prevent slipping during hot yoga sessions, made from 4+ recycled plastic bottles.",
        "category": "Sports & Fitness",
        "price": 60.00,
        "stock": 40,
        "attributes": {"brand": "Manduka", "technology": "Skidless Silicone Nobs", "quick_dry": True}
    },
    {
        "sku": "GYM-GYMNAST-RINGS-WD",
        "name": "Titan Fitness Solid Wood 1.25-Inch Gymnastic Rings with Numbered Straps",
        "description": "Natural textured Baltic birch wood gymnastic rings with 15ft heavy-duty nylon straps featuring carabiners and numbered marks for quick leveling.",
        "category": "Sports & Fitness",
        "price": 49.99,
        "stock": 25,
        "attributes": {"brand": "Titan Fitness", "diameter_in": 1.25, "wood": "Baltic Birch", "strap_length_ft": 15}
    },
    {
        "sku": "PERF-CREAT-MONO-500",
        "name": "Optimum Nutrition Micronized Creatine Monohydrate Powder 600g",
        "description": "100% pure Creapure unflavored micronized creatine monohydrate to support ATP regeneration, muscle energy, strength, and lean power output.",
        "category": "Sports & Fitness",
        "price": 38.99,
        "stock": 60,
        "attributes": {"brand": "Optimum Nutrition", "servings": 120, "form": "Micronized Powder", "unflavored": True}
    },
    {
        "sku": "GOLD-STD-WHEY-5LB",
        "name": "Optimum Nutrition Gold Standard 100% Whey Protein 5 Lbs (Double Rich Chocolate)",
        "description": "24g of whey protein isolate and peptides per serving with 5.5g of naturally occurring BCAAs and 4g of glutamine for post-workout muscle repair.",
        "category": "Sports & Fitness",
        "price": 79.99,
        "stock": 50,
        "attributes": {"brand": "Optimum Nutrition", "protein_per_serving_g": 24, "weight_lbs": 5.0, "flavor": "Double Rich Chocolate"}
    },
    {
        "sku": "NORD-STRAP-HAM-CURL",
        "name": "The Tib Bar Guy Nordic Hamstring Curl Strap for Doorway",
        "description": "High-strength steel doorway strap with dense foam foot rest designed to perform knee-friendly Nordic hamstring curls and ATG split squats anywhere.",
        "category": "Sports & Fitness",
        "price": 44.95,
        "stock": 30,
        "attributes": {"brand": "The Tib Bar Guy", "usage": "Nordic Hamstring Curls", "portable": True}
    },
    {
        "sku": "SBD-KNEE-SLEEVES-7M",
        "name": "SBD Apparel 7mm Neoprene Powerlifting Knee Sleeves (Pair)",
        "description": "IPF approved high-grade 7mm neoprene knee compression sleeves providing maximum joint warmth, stability, and rebound on heavy squats.",
        "category": "Sports & Fitness",
        "price": 95.00,
        "stock": 20,
        "attributes": {"brand": "SBD", "thickness_mm": 7, "ipf_approved": True, "size": "L"}
    },
    {
        "sku": "AB-ROLLER-WHEEL-PRO",
        "name": "Perfect Fitness Ab Carver Pro Roller Wheel with Kinetic Engine",
        "description": "Ultra-wide spherical ab wheel with carbon steel spring kinetic engine providing resistance on rollout and assistance on pullback with ergonomic rubber grips.",
        "category": "Sports & Fitness",
        "price": 39.99,
        "stock": 35,
        "attributes": {"brand": "Perfect Fitness", "mechanism": "Carbon Steel Kinetic Spring", "wheel": "Ultra-Wide"}
    },
    {
        "sku": "LIQ-CHALK-GRIP-250",
        "name": "Spider Chalk Liquid Gym Chalk 8 oz (Pure Magnesium Carbonate)",
        "description": "Mess-free fast-drying laboratory-grade liquid magnesium carbonate gym chalk with zero fillers for rock climbing, gymnastics, and heavy deadlifts.",
        "category": "Sports & Fitness",
        "price": 18.99,
        "stock": 65,
        "attributes": {"brand": "Spider Chalk", "volume_oz": 8, "filler_free": True, "fast_drying": True}
    },

    # ==========================================
    # DOMAIN 9: HEALTH, GROOMING & BEAUTY (28)
    # ==========================================
    {
        "sku": "DYSO-SUPER-HAIR-DRY",
        "name": "Dyson Supersonic Hair Dryer (Iron/Fuchsia) with 5 Attachments",
        "description": "Fast drying with no extreme heat engineered for different hair types, intelligent heat control measures air temperature 40 times per second.",
        "category": "Health & Beauty",
        "price": 429.99,
        "stock": 10,
        "attributes": {"brand": "Dyson", "attachments": 5, "motor": "Dyson Digital Motor V9", "ionic": True}
    },
    {
        "sku": "PHIL-SONIC-9900-PR",
        "name": "Philips Sonicare DiamondClean Prestige 9900 Rechargeable Electric Toothbrush",
        "description": "SenseIQ technology senses pressure, motion, and coverage up to 100 times per second, removing up to 20x more plaque with AI app coaching.",
        "category": "Health & Beauty",
        "price": 379.96,
        "stock": 15,
        "attributes": {"brand": "Philips Sonicare", "technology": "SenseIQ Sonic", "battery_weeks": 2, "case": "USB Leather Charging Case"}
    },
    {
        "sku": "ORALB-IO-SERIES-9",
        "name": "Oral-B iO Series 9 Electric Toothbrush with 3D Teeth Tracking",
        "description": "Revolutionary magnetic iO technology with micro-vibrating bristles, interactive color display, and 3D teeth tracking AI to guide your 2-minute brushing.",
        "category": "Health & Beauty",
        "price": 299.99,
        "stock": 18,
        "attributes": {"brand": "Oral-B", "technology": "Magnetic iO", "display": "Interactive Color", "modes": 7}
    },
    {
        "sku": "BRAUN-SERIES-9-PRO",
        "name": "Braun Series 9 Pro+ Electric Foil Shaver with SmartCare Center",
        "description": "World's most efficient electric shaver with 5 synchronized shaving elements, ProLift trimmer, 40,000 cutting actions per minute, and 6-in-1 SmartCare clean station.",
        "category": "Health & Beauty",
        "price": 379.99,
        "stock": 12,
        "attributes": {"brand": "Braun", "cutting_actions_pm": 40000, "wet_dry": True, "made_in": "Germany"}
    },
    {
        "sku": "CERAVE-MOIST-CRM-16",
        "name": "CeraVe Moisturizing Cream with 3 Essential Ceramides & Hyaluronic Acid 19 oz",
        "description": "Rich, non-greasy daily hydrating face and body cream with MVE delivery technology for 24-hour hydration, fragrance-free and dermatologist recommended.",
        "category": "Health & Beauty",
        "price": 19.99,
        "stock": 90,
        "attributes": {"brand": "CeraVe", "size_oz": 19, "ceramides": "1, 3, 6-II", "fragrance_free": True}
    },
    {
        "sku": "LA-ROCHE-ANTHE-60",
        "name": "La Roche-Posay Anthelios Melt-in Milk Sunscreen SPF 60 (5 oz)",
        "description": "Oxybenzone-free broad spectrum UVA/UVB SPF 60 face and body sunscreen with Cell-Ox Shield antioxidant technology, fast-absorbing and water resistant for 80 min.",
        "category": "Health & Beauty",
        "price": 27.99,
        "stock": 75,
        "attributes": {"brand": "La Roche-Posay", "spf": 60, "water_resistant_min": 80, "dermatologist_tested": True}
    },
    {
        "sku": "WATERP-AQUAP-WP660",
        "name": "Waterpik Aquarius Professional Water Flosser Dental Oral Irrigator",
        "description": "Clinically proven to remove up to 99.9% of plaque from treated areas with 10 pressure settings, Massage Mode for gum stimulation, and 7 tips.",
        "category": "Health & Beauty",
        "price": 79.99,
        "stock": 35,
        "attributes": {"brand": "Waterpik", "pressure_settings": 10, "ada_accepted": True, "capacity_sec": 90}
    },
    {
        "sku": "PAULA-2PCT-BHA-LIQ",
        "name": "Paula's Choice Skin Perfecting 2% BHA Salicylic Acid Liquid Exfoliant 4 oz",
        "description": "Cult-favorite leave-on exfoliant that unclogs enlarged pores, smooths wrinkles, evens skin tone, and clears dead skin cells with gentle green tea extract.",
        "category": "Health & Beauty",
        "price": 35.00,
        "stock": 60,
        "attributes": {"brand": "Paula's Choice", "active": "2% Salicylic Acid BHA", "size_oz": 4.0, "fragrance_free": True}
    },
    {
        "sku": "MANSC-LAWN-MOW-5",
        "name": "MANSCAPED The Lawn Mower 5.0 Ultra Body & Groin Hair Trimmer",
        "description": "Next-gen dual SkinSafe ceramic blade heads, waterproof body, wireless charging dock, dual-temp LED spotlight, and travel lock.",
        "category": "Health & Beauty",
        "price": 109.99,
        "stock": 25,
        "attributes": {"brand": "MANSCAPED", "waterproof": True, "blade": "SkinSafe Ceramic", "wireless_charging": True}
    },
    {
        "sku": "THE-ORD-NIACIN-60",
        "name": "The Ordinary Niacinamide 10% + Zinc 1% Oil Control Serum 60ml",
        "description": "High-strength vitamin and mineral blemish formula that reduces the appearance of skin blemishes, congestion, and balances visible sebum activity.",
        "category": "Health & Beauty",
        "price": 11.20,
        "stock": 100,
        "attributes": {"brand": "The Ordinary", "actives": "10% Niacinamide + 1% Zinc", "volume_ml": 60, "vegan": True}
    },
    {
        "sku": "MAISON-MAR-JAZZ-CLB",
        "name": "Maison Margiela REPLICA Jazz Club Eau de Toilette 100ml",
        "description": "Warm and spicy fragrance capturing the heady atmosphere of a private Brooklyn jazz club with notes of pink pepper, rum absolute, vanilla, and tobacco leaf.",
        "category": "Health & Beauty",
        "price": 160.00,
        "stock": 18,
        "attributes": {"brand": "Maison Margiela", "type": "Eau de Toilette", "volume_ml": 100, "scent": "Warm & Spicy / Rum & Tobacco"}
    },
    {
        "sku": "LE-LABO-SANTAL-33",
        "name": "Le Labo Santal 33 Eau de Parfum 50ml",
        "description": "Iconic genderless perfume composed of cardamom, iris, violet, ambrox, and Australian sandalwood, cedarwood, and spicy leather notes.",
        "category": "Health & Beauty",
        "price": 230.00,
        "stock": 10,
        "attributes": {"brand": "Le Labo", "volume_ml": 50, "type": "Eau de Parfum", "unisex": True}
    },
    {
        "sku": "CREED-AVENT-EDP-100",
        "name": "Creed Aventus Fragrance for Men Eau de Parfum 100ml",
        "description": "Celebrated luxury fragrance opening with vibrant notes of bergamot, blackcurrant, apple, pineapple, birch, patchouli, oakmoss, and ambergris.",
        "category": "Health & Beauty",
        "price": 495.00,
        "stock": 6,
        "attributes": {"brand": "Creed", "volume_ml": 100, "type": "Eau de Parfum", "made_in": "France"}
    },
    {
        "sku": "SKCEUT-CE-FERULIC",
        "name": "SkinCeuticals C E Ferulic Triple Antioxidant Treatment 30ml",
        "description": "Patented daytime vitamin C serum featuring 15% pure L-ascorbic acid, 1% alpha tocopherol, and 0.5% ferulic acid for advanced environmental photoprotection.",
        "category": "Health & Beauty",
        "price": 182.00,
        "stock": 15,
        "attributes": {"brand": "SkinCeuticals", "vitamin_c_pct": 15, "volume_ml": 30, "dermatologist_grade": True}
    },
    {
        "sku": "DYSO-AIRWRAP-CMPLT",
        "name": "Dyson Airwrap Multi-Styler Complete Long (Nickel/Copper)",
        "description": "Styles with Coanda airflow instead of extreme heat, re-engineered barrels that curl in both directions, smoothing brushes, and flyaway attachment.",
        "category": "Health & Beauty",
        "price": 599.99,
        "stock": 8,
        "attributes": {"brand": "Dyson", "technology": "Coanda Airflow", "attachments": 6, "heat_damage": "None"}
    },
    {
        "sku": "AESOP-RESURR-SOAP",
        "name": "Aesop Resurrection Aromatique Hand Wash 500ml",
        "description": "Gentle botanical gel hand cleanser with skin-softening Mandarin Rind, Rosemary Leaf, and Cedar Atlas oils leaving hands refreshed and fragrant.",
        "category": "Health & Beauty",
        "price": 43.00,
        "stock": 45,
        "attributes": {"brand": "Aesop", "volume_ml": 500, "botanical": True, "scent": "Citrus, Woody, Herbaceous"}
    },
    {
        "sku": "OLAPLEX-NO3-HAIR-TRT",
        "name": "Olaplex No. 3 Hair Perfector Repairing Treatment 100ml",
        "description": "Weekly pre-shampoo hair bond builder that dramatically repairs damaged, broken disulfide bonds caused by chemical bleaching and heat styling.",
        "category": "Health & Beauty",
        "price": 30.00,
        "stock": 70,
        "attributes": {"brand": "Olaplex", "technology": "Bis-Aminopropyl Diglycol Dimaleate", "volume_ml": 100}
    },
    {
        "sku": "PANAS-ARC5-SHAVER",
        "name": "Panasonic Arc5 Cordless Electric Razor with Multi-Flex 16D Head",
        "description": "5 ultra-sharp precision honed 30-degree Nanotech blades powered by a 14,000 CPM linear motor with automatic smart shave sensor.",
        "category": "Health & Beauty",
        "price": 209.99,
        "stock": 20,
        "attributes": {"brand": "Panasonic", "blades": 5, "motor_cpm": 14000, "flex_head": "16-D"}
    },
    {
        "sku": "LANEIGE-LIP-SLP-MSK",
        "name": "LANEIGE Lip Sleeping Mask Intensive Hydration (Berry, 20g)",
        "description": "Nourishing overnight lip mask enriched with Berry Fruit Complex, Vitamin C, and coconut oil to deliver intense moisture and eliminate flaky lips.",
        "category": "Health & Beauty",
        "price": 24.00,
        "stock": 80,
        "attributes": {"brand": "LANEIGE", "flavor": "Berry", "weight_g": 20, "overnight": True}
    },
    {
        "sku": "MUHLE-R89-SAF-RAZ",
        "name": "Mühle R89 Traditional Closed Comb Double Edge Safety Razor",
        "description": "German handcrafted classic double-edge safety razor with precision chrome-plated finish and engraved knurled grip for a zero-irritation wet shave.",
        "category": "Health & Beauty",
        "price": 46.00,
        "stock": 30,
        "attributes": {"brand": "Mühle", "type": "Double Edge Safety Razor", "material": "Chrome-Plated Metal", "made_in": "Germany"}
    },
    {
        "sku": "SOL-DE-JANEIRO-68",
        "name": "Sol de Janeiro Brazilian Bum Bum Cream 240ml (Pistachio & Salted Caramel)",
        "description": "Fast-absorbing body cream infused with caffeine-rich Guaraná extract, cupuaçu butter, and coconut oil that visibly tightens and smooths skin.",
        "category": "Health & Beauty",
        "price": 48.00,
        "stock": 50,
        "attributes": {"brand": "Sol de Janeiro", "volume_ml": 240, "scent": "Cheirosa 62", "tightening": True}
    },
    {
        "sku": "NUFACE-TRIN-FACIAL",
        "name": "NuFACE Trinity+ Advanced Microcurrent Facial Toning Device",
        "description": "FDA-cleared microcurrent device that activates facial muscles to visibly tone, lift, and contour the jawline, cheeks, and neck in 5 minutes a day.",
        "category": "Health & Beauty",
        "price": 395.00,
        "stock": 8,
        "attributes": {"brand": "NuFACE", "technology": "Microcurrent", "fda_cleared": True, "rechargeable": True}
    },
    {
        "sku": "SUPERG-UNSEEN-SPF40",
        "name": "Supergoop! Unseen Sunscreen SPF 40 Invisible Makeup Primer 1.7 oz",
        "description": "100% invisible, weightless, scentless oil-free broad spectrum sunscreen with a velvety natural finish that doubles as a makeup-gripping primer.",
        "category": "Health & Beauty",
        "price": 38.00,
        "stock": 65,
        "attributes": {"brand": "Supergoop!", "spf": 40, "finish": "Invisible Matte", "oil_free": True}
    },
    {
        "sku": "AVEDA-ROSM-MINT-SHP",
        "name": "Aveda Rosemary Mint Purifying Shampoo 1000ml (Liter Size)",
        "description": "97% naturally derived clarifying shampoo with organic rosemary and peppermint that gently cleanses impurities and adds weightless volume and shine.",
        "category": "Health & Beauty",
        "price": 68.00,
        "stock": 25,
        "attributes": {"brand": "Aveda", "volume_ml": 1000, "scent": "Rosemary Peppermint", "cruelty_free": True}
    },
    {
        "sku": "T3-MICRO-CUR-IRON-125",
        "name": "T3 SinglePass Curl 1.25-Inch Ceramic Professional Curling Iron",
        "description": "Custom blend ceramic barrel with digital T3 SinglePass technology ensures even heat without hot spots, 5 heat settings, and 1-hour auto shut-off.",
        "category": "Health & Beauty",
        "price": 169.99,
        "stock": 16,
        "attributes": {"brand": "T3 Micro", "barrel_diameter_in": 1.25, "heat_settings": 5, "material": "Custom Ceramic"}
    },
    {
        "sku": "NEOM-ORGAN-DIFF-WELL",
        "name": "NEOM Wellbeing Pod Essential Oil Ultrasonic Aroma Diffuser",
        "description": "Crafted from heavy ceramic stone with rose gold detail, releases 100% natural aromatherapy essential oil mists with warm LED nightlight and timer.",
        "category": "Health & Beauty",
        "price": 110.00,
        "stock": 22,
        "attributes": {"brand": "NEOM Organics", "material": "White Ceramic Stone", "timer_hours": "1, 2, 3, 4"}
    },
    {
        "sku": "DR-BRON-PEP-CAST-32",
        "name": "Dr. Bronner's 18-in-1 Pure Castile Liquid Soap (Peppermint, 32 oz)",
        "description": "Concentrated biodegradable organic castile soap made with organic fair trade oils and certified organic peppermint essential oil for face, body, and home.",
        "category": "Health & Beauty",
        "price": 16.99,
        "stock": 80,
        "attributes": {"brand": "Dr. Bronner's", "size_oz": 32, "organic": True, "fair_trade": True}
    },
    {
        "sku": "OMRON-PLAT-BP-MON",
        "name": "Omron Platinum Upper Arm Wireless Blood Pressure Monitor",
        "description": "Clinically validated upper arm blood pressure monitor with dual LCD display, High Morning Average alerts, irregular heartbeat detection, and Bluetooth app.",
        "category": "Health & Beauty",
        "price": 89.99,
        "stock": 30,
        "attributes": {"brand": "Omron", "fda_cleared": True, "connectivity": "Bluetooth Smart", "memory": "200 Readings"}
    },

    # ==========================================
    # DOMAIN 10: GAMING, AUDIO & HOBBIES (28)
    # ==========================================
    {
        "sku": "SONY-PS5-SLIM-DISC",
        "name": "PlayStation 5 Slim Console (Disc Edition) 1TB SSD",
        "description": "Sleek slim chassis with 1TB ultra-high-speed SSD, Tempest 3D AudioTech, ray tracing hardware acceleration, 4K@120Hz gaming, and DualSense haptic feedback.",
        "category": "Gaming & Entertainment",
        "price": 499.99,
        "stock": 10,
        "attributes": {"brand": "Sony PlayStation", "storage_ssd_tb": 1.0, "optical_drive": "Ultra HD Blu-Ray", "resolution": "4K@120Hz"}
    },
    {
        "sku": "META-QUEST-3-128",
        "name": "Meta Quest 3 Mixed Reality VR Headset 128GB",
        "description": "Next-gen breakthrough mixed reality with 4K+ Infinite Display, Snapdragon XR2 Gen 2 performance, Touch Plus controllers with TruTouch haptics.",
        "category": "Gaming & Entertainment",
        "price": 499.99,
        "stock": 14,
        "attributes": {"brand": "Meta", "storage": "128GB", "mixed_reality": "Full-Color Passthrough", "chip": "Snapdragon XR2 Gen 2"}
    },
    {
        "sku": "VALV-STEAM-DCK-512",
        "name": "Valve Steam Deck OLED 512GB Handheld Gaming PC",
        "description": "7.4-inch 90Hz HDR OLED screen with 1,000,000:1 contrast, 6nm AMD APU, 50Wh battery for 3-12 hours of gameplay, full-size thumbsticks and dual trackpads.",
        "category": "Gaming & Entertainment",
        "price": 549.00,
        "stock": 8,
        "attributes": {"brand": "Valve", "display": "7.4 inch 90Hz OLED HDR", "storage": "512GB NVMe", "battery_wh": 50}
    },
    {
        "sku": "NINT-SWTCH-OLED-WHT",
        "name": "Nintendo Switch OLED Model with White Joy-Con",
        "description": "Vibrant 7-inch OLED screen, wide adjustable tabletop stand, dock with wired LAN port, 64GB internal storage, and enhanced onboard audio.",
        "category": "Gaming & Entertainment",
        "price": 349.99,
        "stock": 20,
        "attributes": {"brand": "Nintendo", "screen": "7-inch OLED", "storage": "64GB", "color": "White Joy-Con"}
    },
    {
        "sku": "XBOX-SER-X-1TB",
        "name": "Xbox Series X 1TB Gaming Console (4K 120FPS)",
        "description": "12 teraflops of raw graphic processing power, DirectX Raytracing, Quick Resume across multiple games, custom 1TB NVMe SSD, and 4K UHD Blu-ray.",
        "category": "Gaming & Entertainment",
        "price": 499.99,
        "stock": 10,
        "attributes": {"brand": "Microsoft Xbox", "gpu_teraflops": 12, "storage": "1TB Custom SSD", "ray_tracing": True}
    },
    {
        "sku": "STEL-ARCT-NOV-PRO",
        "name": "SteelSeries Arctis Nova Pro Wireless Multi-System Gaming Headset",
        "description": "Premium High Fidelity audio drivers with Active Noise Cancellation, Infinity Power System with 2 hot-swappable batteries, simultaneous 2.4GHz & Bluetooth.",
        "category": "Gaming & Entertainment",
        "price": 349.99,
        "stock": 16,
        "attributes": {"brand": "SteelSeries", "audio": "Hi-Res Nova Pro", "anc": True, "dual_wireless": True}
    },
    {
        "sku": "LOGI-G-PRO-X-SUPER2",
        "name": "Logitech G PRO X SUPERLIGHT 2 Lightweight Wireless Gaming Mouse",
        "description": "60g ultra-lightweight esports icon with HERO 2 sensor up to 32,000 DPI, LIGHTFORCE hybrid optical-mechanical switches, and 2000Hz polling rate.",
        "category": "Gaming & Entertainment",
        "price": 159.99,
        "stock": 30,
        "attributes": {"brand": "Logitech G", "weight_g": 60, "sensor_dpi": 32000, "polling_hz": 2000, "color": "Black"}
    },
    {
        "sku": "LOGI-G29-RACE-WHEEL",
        "name": "Logitech G29 Driving Force Racing Wheel and Floor Pedals",
        "description": "Dual-motor force feedback racing wheel with helical gearing to simulate realistic road feel, 900-degree lock-to-lock rotation, and responsive steel pedals.",
        "category": "Gaming & Entertainment",
        "price": 269.99,
        "stock": 12,
        "attributes": {"brand": "Logitech G", "rotation_degrees": 900, "feedback": "Dual-Motor Force", "pedals": "3-Pedal Stainless"}
    },
    {
        "sku": "ELGAT-4K-X-CAPTUR",
        "name": "Elgato 4K X External USB 3.2 Gen 2 Game Capture Card",
        "description": "Ultra-low latency game capture up to 4K144 or 1080p240 HDR passthrough with HDMI 2.1, variable refresh rate (VRR), and plug-and-play USB-C connectivity.",
        "category": "Gaming & Entertainment",
        "price": 229.99,
        "stock": 18,
        "attributes": {"brand": "Elgato", "passthrough": "4K144 / 1080p240", "interface": "HDMI 2.1 / USB-C 3.2", "vrr": True}
    },
    {
        "sku": "RAZR-KISHI-V2-PRO",
        "name": "Razer Kishi V2 Pro Mobile Gaming Controller for Android (USB-C)",
        "description": "Universal mobile controller with HyperSense haptic feedback, microswitch buttons, analog triggers, programmable multifunction buttons, and 3.5mm audio.",
        "category": "Gaming & Entertainment",
        "price": 129.99,
        "stock": 25,
        "attributes": {"brand": "Razer", "haptics": "HyperSense", "connector": "USB-C Zero-Latency", "pass_through_charging": True}
    },
    {
        "sku": "AUD-TECH-LP120XUSB",
        "name": "Audio-Technica AT-LP120XUSB Direct-Drive Turntable (Analog & USB)",
        "description": "Professional direct-drive turntable with selectable 33/45/78 RPM speeds, AT-VM95E dual magnet phono cartridge, adjustable dynamic anti-skate control, and USB output.",
        "category": "Gaming & Entertainment",
        "price": 349.00,
        "stock": 14,
        "attributes": {"brand": "Audio-Technica", "drive": "Direct-Drive DC", "cartridge": "AT-VM95E", "usb_out": True}
    },
    {
        "sku": "LAMY-2000-FOUN-MED",
        "name": "Lamy 2000 Makrolon Piston Fountain Pen (14K Gold Medium Nib)",
        "description": "Modern design classic crafted from fiberglass-reinforced Makrolon resin with brushed stainless steel grip and platinum-coated 14K gold semi-hooded nib.",
        "category": "Gaming & Entertainment",
        "price": 199.00,
        "stock": 20,
        "attributes": {"brand": "Lamy", "nib": "14K Gold Medium", "filling": "Piston Mechanism", "material": "Black Makrolon"}
    },
    {
        "sku": "LEUCH-1917-A5-DOT",
        "name": "Leuchtturm1917 A5 Medium Hardcover Dotted Journal (Pacific Green)",
        "description": "251 numbered pages of ink-proof 80 g/m2 acid-free paper, 8 perforated sheets, expandable inside back pocket, 2 ribbon bookmarks, and table of contents.",
        "category": "Gaming & Entertainment",
        "price": 24.50,
        "stock": 50,
        "attributes": {"brand": "Leuchtturm1917", "pages": 251, "paper_weight_gsm": 80, "ruling": "Dot Grid", "size": "A5"}
    },
    {
        "sku": "MIDOR-TRAV-LEATH-REG",
        "name": "Traveler's Company Japan Leather Traveler's Notebook Regular (Brown)",
        "description": "Handmade Chiang Mai vegetable-tanned thick leather cover with customizable elastic binding system and premium bleed-resistant Midori MD paper refill.",
        "category": "Gaming & Entertainment",
        "price": 54.00,
        "stock": 30,
        "attributes": {"brand": "Traveler's Company", "leather": "Vegetable-Tanned Cowhide", "paper": "Midori MD", "made_in": "Japan"}
    },
    {
        "sku": "CATAN-BRD-GAME-5TH",
        "name": "Catan Strategy Board Game 5th Edition (3-4 Players)",
        "description": "Award-winning strategy game where players trade, build, and settle the island of Catan with modular hex tiles for endless replayability.",
        "category": "Gaming & Entertainment",
        "price": 47.99,
        "stock": 40,
        "attributes": {"brand": "Catan Studio", "players": "3 to 4", "play_time_min": 60, "type": "Strategy Board Game"}
    },
    {
        "sku": "WINGS-BRD-GAME-ED",
        "name": "Wingspan Board Game with Swift-Start Pack (Stonemaier Games)",
        "description": "Competitive bird-collection engine-building board game featuring 170 unique illustrated bird cards, custom pastel eggs, and dice tower birdfeeder.",
        "category": "Gaming & Entertainment",
        "price": 59.95,
        "stock": 25,
        "attributes": {"brand": "Stonemaier Games", "players": "1 to 5", "designer": "Elizabeth Hargrave", "rating": 8.1}
    },
    {
        "sku": "WACOM-INTUOS-PRO-M",
        "name": "Wacom Intuos Pro Medium Creative Graphics Drawing Tablet",
        "description": "Professional drawing tablet with Pro Pen 2 offering 8192 levels of pressure sensitivity, tilt recognition, 8 customizable ExpressKeys, and multi-touch surface.",
        "category": "Gaming & Entertainment",
        "price": 379.95,
        "stock": 15,
        "attributes": {"brand": "Wacom", "pressure_levels": 8192, "active_area_in": "8.7 x 5.8", "connectivity": "Bluetooth & USB"}
    },
    {
        "sku": "RODE-PODMIC-XLR",
        "name": "Rode PodMic Dynamic Podcasting Broadcast Microphone",
        "description": "Broadcast-grade dynamic microphone optimized for speech and podcasting with internal pop filter, solid all-metal construction, and integrated swing mount.",
        "category": "Gaming & Entertainment",
        "price": 99.00,
        "stock": 35,
        "attributes": {"brand": "Rode", "polar_pattern": "Cardioid", "type": "Dynamic XLR", "usage": "Podcasting"}
    },
    {
        "sku": "FOCUSR-SCAR-2I2-G4",
        "name": "Focusrite Scarlett 2i2 4th Gen USB Audio Interface",
        "description": "Next-gen audio interface with 120dB dynamic range RedNet converters, Auto Gain, Clip Safe, Air Mode with Presence and Harmonic Drive, and Loopback.",
        "category": "Gaming & Entertainment",
        "price": 199.99,
        "stock": 22,
        "attributes": {"brand": "Focusrite", "inputs": 2, "dynamic_range_db": 120, "auto_gain": True}
    },
    {
        "sku": "BEYR-DT990-PRO-250",
        "name": "Beyerdynamic DT 990 PRO 250 Ohm Open-Back Studio Headphones",
        "description": "Handcrafted in Germany open-back studio reference headphones with wide three-dimensional acoustic stage, spring steel headband, and plush velour earpads.",
        "category": "Gaming & Entertainment",
        "price": 169.00,
        "stock": 25,
        "attributes": {"brand": "Beyerdynamic", "impedance_ohms": 250, "design": "Open-Back", "made_in": "Germany"}
    },
    {
        "sku": "SONY-DUALSEN-EDGE",
        "name": "PlayStation DualSense Edge Wireless Pro Controller",
        "description": "High-performance customizable PS5 controller with replaceable stick modules, remappable back buttons, adjustable trigger stops, and custom profiles.",
        "category": "Gaming & Entertainment",
        "price": 199.99,
        "stock": 14,
        "attributes": {"brand": "Sony PlayStation", "swappable_sticks": True, "back_buttons": 2, "trigger_stops": True}
    },
    {
        "sku": "XBOX-ELITE-SER2-BLK",
        "name": "Xbox Elite Wireless Controller Series 2 (Black)",
        "description": "Pro controller with adjustable-tension thumbsticks, wrap-around rubberized grip, shorter hair trigger locks, up to 40 hours of rechargeable battery.",
        "category": "Gaming & Entertainment",
        "price": 179.99,
        "stock": 15,
        "attributes": {"brand": "Microsoft Xbox", "battery_hours": 40, "thumbstick_tension": "Adjustable", "paddles": 4}
    },
    {
        "sku": "KOSS-PORTA-PRO-CLAS",
        "name": "Koss Porta Pro Classic On-Ear Lightweight Headphones with ComfortZone",
        "description": "Legendary retro lightweight portable headphones with ComfortZone temporal pad adjustment, oxygen-free copper voice coils, and collapsible headband.",
        "category": "Gaming & Entertainment",
        "price": 49.99,
        "stock": 50,
        "attributes": {"brand": "Koss", "frequency_hz": "15-25,000", "comfort_zone": True, "connector": "3.5mm Jack"}
    },
    {
        "sku": "LOOP-EXPER-PLUS-EAR",
        "name": "Loop Experience Plus High-Fidelity Concert Noise Reducing Earplugs",
        "description": "Acoustic channel earplugs providing 18dB (or 23dB with Mute accessory) of even noise attenuation while maintaining pristine music sound clarity.",
        "category": "Gaming & Entertainment",
        "price": 44.95,
        "stock": 60,
        "attributes": {"brand": "Loop", "snr_reduction_db": 18, "reusable": True, "color": "Midnight Black"}
    },
    {
        "sku": "ROTR-600-MECH-PENC",
        "name": "rOtring 600 0.5mm Mechanical Pencil (Matte Black Full Metal)",
        "description": "Iconic full metal hexagonal brass body preventing table rolling, knurled metal grip, lead hardness grade indicator, and fixed lead guidance sleeve.",
        "category": "Gaming & Entertainment",
        "price": 32.00,
        "stock": 45,
        "attributes": {"brand": "rOtring", "lead_size_mm": 0.5, "material": "Solid Brass", "color": "Matte Black"}
    },
    {
        "sku": "TAMI-EXTRA-THIN-CEM",
        "name": "Tamiya Extra Thin Liquid Cement for Plastic Model Kits 40ml",
        "description": "Capillary action fast-setting liquid polystyrene cement with fine precision applicator brush for plastic Gundam, aircraft, and armor model joints.",
        "category": "Gaming & Entertainment",
        "price": 9.99,
        "stock": 100,
        "attributes": {"brand": "Tamiya", "volume_ml": 40, "action": "Capillary Flow", "made_in": "Japan"}
    },
    {
        "sku": "VALLEJO-BASIC-72SET",
        "name": "Vallejo Model Color Acrylic Paint Basic 16-Color Set with Droppers",
        "description": "16 non-toxic water-based matte acrylic paints in 17ml eyedropper bottles with ultra-fine pigment formulation designed for miniature painting and resin models.",
        "category": "Gaming & Entertainment",
        "price": 49.99,
        "stock": 30,
        "attributes": {"brand": "Vallejo", "colors_count": 16, "bottle_ml": 17, "formula": "Matte Acrylic"}
    },
    {
        "sku": "KOPL-100-DOBL-SLV",
        "name": "Dragon Shield Matte Card Sleeves 100-Pack Standard Size (Jet Black)",
        "description": "Tough polypropylene card sleeves with textured matte back for supreme shuffle feel, archival safe, fits Magic: The Gathering and Pokémon cards.",
        "category": "Gaming & Entertainment",
        "price": 13.99,
        "stock": 120,
        "attributes": {"brand": "Dragon Shield", "count": 100, "material": "Polypropylene", "color": "Matte Jet"}
    }
]

CATALOG_PRODUCTS = CATALOG_ITEMS

