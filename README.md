# Hazard Marker Detection and Placement

**ROS2 Search & Navigation Challenge **

ระบบตรวจจับป้ายอันตราย (Hazard Markers) และระบุตำแหน่งบนแผนที่โดยอัตโนมัติ สำหรับ ROSBot Pro 3.0/2.0

---

## 📋 All content

- [ภาพรวมระบบ](#-ภาพรวมระบบ)
- [สิ่งที่ต้องการก่อนรัน](#-สิ่งที่ต้องการก่อนรัน)
- [โครงสร้างไฟล์](#-โครงสร้างไฟล์)
- [การติดตั้ง](#-การติดตั้ง)
- [วิธีรัน](#-วิธีรัน)
- [Flowchart การทำงาน](#-flowchart-การทำงาน)
- [ขั้นตอนโปรแกรมแบบละเอียด](#-ขั้นตอนโปรแกรมแบบละเอียด)
- [Topics ทั้งหมด](#-topics-ทั้งหมด)
- [Nodes ที่รันขึ้นมา](#-nodes-ที่รันขึ้นมา)
- [Parameters](#-parameters)
- [Hazard Marker IDs](#-hazard-marker-ids)
- [การ Debug](#-การ-debug)
- [ข้อจำกัดและแนวทางแก้ไข](#-ข้อจำกัดและแนวทางแก้ไข)

---

## 🧭 Overview

```
กล้อง RGB ──→ จำรูปป้าย ──→ คำนวณตำแหน่ง ──→ Markบนแผนที่
  (OAK-D)    (find_object_2d)  (laser + TF)     (/hazards topic)
```

### ป้ายที่ต้องค้นหา (ตัวอย่าง)

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  💥 Explosive│  │ 🔥 Flammable│  │ ☢️ Radioactive│
│    ID: 1    │  │   ID: 2     │  │   ID: 11    │
└─────────────┘  └─────────────┘  └─────────────┘
```

---

## 🔧 System Need

### Hardware

| อุปกรณ์ | รายละเอียด |
|---------|------------|
| ROSBot Pro 3.0 / 2.0 | Robot |
| OAK-D Camera | Camera RGB for detect |
| RPLIDAR | Lidar scan 360° |

### Software (prerequisite)

**ต้องรันทั้ง 3 Node นี้ก่อนที่จะ launch Node **

```
Node 1: ROSBot Hardware Driver
          └── publish: /oak/rgb/image_raw/compressed
          └── publish: /scan
          └── publish: /tf (base_link, odom)

Node 2: SLAM Toolbox + Nav2
          └── subscribe: /scan
          └── publish: /map
          └── publish: /tf (map → odom → base_link)

Node 3: ← Node ของเรา (hazard_detector.launch.py)
```

### ROS2 Package Dependencies

```xml
rclpy
geometry_msgs
visualization_msgs
sensor_msgs
std_msgs
tf2
tf2_ros
tf2_geometry_msgs
find_object_2d       ← install เพิ่ม
aiil_rosbot_demo     ← ต้องมีใน workspace เดียวกัน
```

---

## 📁 File structure

```
snc_team/
├── launch/
│   └── hazard_detector.launch.py    ← Launch ตัวนี้เพื่อ run ทั้ง node ของเรา
├── snc_team/
│   ├── __init__.py
│   └── hazard_detector.py           ← main code 
├── package.xml
└── setup.py
```

---

## 📦 การติดตั้ง

```bash
# 1. clone หรือวางแพ็กเกจใน workspace
cd ~/your_ws/src
# (วาง snc_team และ aiil_rosbot_demo ไว้ที่นี่)

# 2. ติดตั้ง find_object_2d
sudo apt install ros-humble-find-object-2d

# 3. build
cd ~/your_ws
colcon build --packages-select snc_team aiil_rosbot_demo --symlink-install

# 4. source
source install/setup.bash
```

---

## 🚀 HOW TO

### Real Robot

```bash
ros2 launch snc_team hazard_detector.launch.py \
  use_sim_time:=false \
  objects_path:=/path/to/your/hazard_images
```

### Simulator (Gazebo)

```bash
ros2 launch snc_team hazard_detector.launch.py \
  image_topic:=/camera/color/image_raw \
  use_compressed:=false \
  objects_path:=/path/to/your/hazard_images
```

### DUMMY

```bash
ros2 launch snc_team hazard_detector.launch.py \
  objects_path:=/home/user/ws/src/objects_example \
  image_topic:=/oak/rgb/image_raw/compressed \
  use_compressed:=true \
  confirm_frames:=3 \
  duplicate_threshold:=0.5 \
  gui:=true
```

---

## 🔀 Flowchart

### Overview 3 Nodes ที่ทำงานพร้อมกัน

```
┌──────────────────────────────────────────────────────────────────┐
│                   hazard_detector.launch.py                       │
│                                                                    │
│  ┌──────────────────┐   ┌──────────────────┐   ┌──────────────┐  │
│  │ best_effort_     │   │  find_object_2d  │   │  hazard_     │  │
│  │ repeater         │   │                  │   │  detector    │  │
│  │                  │   │  จำรูปป้าย        │   │  ← โค้ดเรา  │  │
│  │  แปลง QoS        │   │  ป้าย 13 ประเภท  │   │              │  │
│  │  BestEffort      │──→│                  │──→│              │  │
│  │  → Reliable      │   │                  │   │              │  │
│  └────────▲─────────┘   └──────────────────┘   └──────┬───────┘  │
│           │                                            │          │
└───────────┼────────────────────────────────────────────┼──────────┘
            │                                            │
     /oak/rgb/image_raw                          /hazards topic
     /compressed                                 /snc_status topic
     (จากกล้อง)
```

### Main Flowchart (hazard_detector node)

```
                    ┌─────────────────┐
                    │   เริ่มต้น Node  │
                    │  (subscribe     │
                    │  /objects +     │
                    │   /scan)        │
                    └────────┬────────┘
                             │
             ┌───────────────┴───────────────┐
             │                               │
    ┌────────▼────────┐             ┌────────▼────────┐
    │  laser_callback │             │objects_callback  │
    │                 │             │                  │
    │  บันทึกค่า      │             │  รับ object_id   │
    │  ranges[]       │             │  + bbox_center_x │
    │  angle_min      │             │                  │
    │  angle_increment│             └────────┬────────┘
    └─────────────────┘                      │
                                   ┌─────────▼─────────┐
                                   │  Start Marker?    │
                                   │  (object_id==13)  │
                                   └───┬───────────┬───┘
                                 ไม่ใช่  │           │   ใช่
                                       ▼           ▼
                                     ข้าม   ┌──────────────┐
                                            │ คำนวณมุม     │
                                            │ จาก pixel    │
                                            │ → radian     │
                                            └──────┬───────┘
                                                   │
                                            ┌──────▼───────┐
                                            │  อ่าน Laser  │
                                            │  ระยะตามมุม  │
                                            │  นั้น (dist) │
                                            └──────┬───────┘
                                                   │
                                      inf/nan? ────┤
                                           ▲       │ ปกติ
                                          ข้าม     ▼
                                            ┌──────────────┐
                                            │  x = dist×cos│
                                            │  y = dist×sin│
                                            │  (base_link) │
                                            └──────┬───────┘
                                                   │
                                            ┌──────▼───────┐
                                            │  TF transform│
                                            │  base_link   │
                                            │  → map frame │
                                            └──────┬───────┘
                                                   │
                                       ล้มเหลว? ───┤
                                           ▲       │ สำเร็จ
                                          warn      ▼
                                            ┌──────────────┐
                                            │  accumulate  │
                                            │  detection   │
                                            │  (debounce)  │
                                            └──────┬───────┘
                                                   │
                                       ยังไม่ครบ ──┤
                                           ▲       │ ครบ 3 frames
                                          รอ        ▼
                                            ┌──────────────┐
                                            │   duplicate  │
                                            │   check      │
                                            │   (< 0.5m?)  │
                                            └──────┬───────┘
                                                   │
                                          ซ้ำ? ────┤
                                           ▲       │ ไม่ซ้ำ
                                          ข้าม     ▼
                                            ┌──────────────┐
                                            │   บันทึก +   │
                                            │   publish    │
                                            │  /hazards    │
                                            │  /snc_status │
                                            └──────────────┘
                                                   │
                              ┌────────────────────┘
                              │  Timer (ทุก 1 วิ)
                              ▼
                    ┌─────────────────┐
                    │  republish      │
                    │  ทุก hazard     │
                    │  ที่ confirm    │
                    │  แล้ว          │
                    └─────────────────┘
```

---

## 📖 Step to run

### ขั้นที่ 0 — เตรียม prerequisite

ก่อน launch Node hazard ต้องมี 3 ชั้นนี้ทำงานอยู่แล้ว:

```
[ชั้น 1] ROSBot Driver
ros2 launch rosbot_xl_bringup bringup.launch.py
    │
    ├── /oak/rgb/image_raw/compressed  (กล้อง OAK-D)
    ├── /scan                          (RPLIDAR)
    └── /tf  base_link ← odom

[ชั้น 2] SLAM + Navigation
ros2 launch slam_toolbox online_async_launch.py
    │
    ├── /map               (OccupancyGrid)
    └── /tf  map ← odom ← base_link  ← สำคัญมาก!

⚠️  ถ้า /tf map→base_link ไม่มี → Node hazard จะ warn ทุก callback
```

### ขั้นที่ 1 — รัน launch file

```bash
ros2 launch snc_team hazard_detector.launch.py \
  use_sim_time:=false \
  objects_path:=/path/to/your/hazard_images```
```
PID xxxxx  →  find_object_2d      (จำรูปป้าย)
PID xxxxx  →  best_effort_repeater (แปลง QoS)
PID xxxxx  →  hazard_detector      (โค้ดเรา)
```

### ขั้นที่ 2 — best_effort_repeater ทำงาน

```
กล้อง OAK-D
    │
    │  /oak/rgb/image_raw/compressed
    │  (CompressedImage · BestEffort QoS)
    │  ← ยอมทิ้ง frame เพื่อความเร็ว
    ▼
best_effort_repeater
    │  รับ compressed image
    │  → แตก compress ด้วย cv_bridge
    │  → re-publish แบบ Reliable QoS
    │
    │  /oak/rgb/image_raw/compressed/repeat
    │  (Image · Reliable QoS)
    ▼
find_object_2d
    (รับแค่ Reliable เท่านั้น)
```

> **ทำไมต้องมี repeater?**
> กล้อง publish แบบ BestEffort (ส่งเร็ว ยอมทิ้ง frame ได้) แต่
> `find_object_2d` รับแค่ Reliable (ต้องได้ทุก frame) — QoS ไม่ตรงกัน
> ข้อมูลจะไม่ถูกส่งเลยถ้าไม่มี repeater เป็นตัวกลาง

### ขั้นที่ 3 — find_object_2d ตรวจจับป้าย

```
find_object_2d โหลดรูปป้ายจาก objects_path/
    │
    ├── 1_Explosive.png
    ├── 2_FlammableGas.png
    ├── ...
    └── 12_Corrosive.png
    │
    ▼  เปรียบเทียบ feature ในภาพจากกล้อง
       กับรูปป้ายที่โหลดไว้ (SIFT/ORB)
    │
    ▼  ถ้าเจอ → publish /objects
       data = [object_id, img_w, img_h, h0..h8, ...]
               ───┬────   ──┬──               ──┬──
                  │          │                   │
               ID ป้าย   ขนาดภาพ            Homography
               (1-13)                        matrix
```

### ขั้นที่ 4 — hazard_detector คำนวณตำแหน่ง

```
objects_callback รับ /objects
        │
        ▼
1. แยก object_id และ bbox center x
   bbox_center_x = img_width / 2.0  (จาก homography)

2. คำนวณมุมในโลกจริง
   angle = (bbox_center_x - image_width/2) / image_width × hfov_rad
   ตัวอย่าง: pixel 480/640, hfov=69° → angle = +10.8°

3. หาระยะจาก Laser
   laser_index = (angle - angle_min) / angle_increment
   distance = ranges[laser_index]
   ถ้า inf/nan/≤0.05m → ข้าม

4. คำนวณ x,y ใน base_link frame
   x_base = distance × cos(angle)
   y_base = distance × sin(angle)

5. แปลง base_link → map ด้วย TF
   pose_in_baselink = PoseStamped(frame="base_link", x, y)
   pose_in_map = tf_buffer.transform(pose, "map")
   ← ต้องมี /tf map→base_link อยู่ก่อน
```

### ขั้นที่ 5 — Debounce (ป้องกันการตรวจจับผิด)

```
ตรวจจับครั้งที่ 1:  pending[id] = {x:1.23, y:0.45, count:1}
ตรวจจับครั้งที่ 2:  ห่างจากเดิม < 0.5m? → count=2, เฉลี่ยตำแหน่ง
ตรวจจับครั้งที่ 3:  count=3 → ✅ CONFIRM!

ถ้าตำแหน่งกระโดด > 0.5m → reset count=1 (อาจเป็น false positive)
```

```
Frame 1:  ┌─────┐  detect Explosive at (1.23, 0.45) → count=1
Frame 2:  │     │  detect Explosive at (1.21, 0.47) → count=2  ┐
Frame 3:  └─────┘  detect Explosive at (1.22, 0.44) → count=3  ┘ CONFIRM!
                                                                  publish!
```

### ขั้นที่ 6 — Publish ผลลัพธ์

```
/hazards  (visualization_msgs/Marker)
    frame_id = "map"    ← พิกัดในแผนที่
    id       = 1        ← Explosive
    type     = SPHERE
    position = (1.22, 0.46, 0.0)
    color    = orange-red
    scale    = 0.3m
    lifetime = 0        ← ไม่หาย

/snc_status  (std_msgs/String)
    "Detected Explosive at (1.22, 0.46). Total found: 1/5"
```

---

## 📡 All Topics 

### Topics ที่ Node รับ (Subscribe)

| Topic | Message Type | QoS | คำอธิบาย |
|-------|-------------|-----|----------|
| `/objects` | `std_msgs/Float32MultiArray` | Reliable | ผลตรวจจับป้ายจาก find_object_2d |
| `/scan` | `sensor_msgs/LaserScan` | BestEffort | ระยะ laser รอบตัว 360° |
| `/tf` + `/tf_static` | `tf2_msgs/TFMessage` | - | Transform tree (map→base_link) |

### Topics ที่ Node ส่ง (Publish)

| Topic | Message Type | QoS | คำอธิบาย |
|-------|-------------|-----|----------|
| `/hazards` | `visualization_msgs/Marker` | Reliable | ตำแหน่งป้ายบนแผนที่ |
| `/snc_status` | `std_msgs/String` | Reliable | สถานะการทำงาน |

### Topics ภายใน Pipeline

| Topic | จาก → ถึง | คำอธิบาย |
|-------|-----------|----------|
| `/oak/rgb/image_raw/compressed` | กล้อง → repeater | raw image BestEffort |
| `/oak/rgb/image_raw/compressed/repeat` | repeater → find_object_2d | ภาพ Reliable |

---

## ⚙️ Nodes

```
ros2 launch snc_team hazard_detector.launch.py
│
├── [1] find_object_2d
│       package:    find_object_2d
│       subscribe:  /oak/rgb/.../repeat  (Reliable)
│       publish:    /objects
│       param:      objects_path, gui, settings_path
│
├── [2] best_effort_repeater
│       package:    aiil_rosbot_demo
│       subscribe:  /oak/rgb/image_raw/compressed  (BestEffort)
│       publish:    /oak/rgb/image_raw/compressed/repeat  (Reliable)
│
└── [3] hazard_detector  ← โค้ดของเรา
        package:    snc_team
        subscribe:  /objects, /scan
        uses TF:    base_link → map
        publish:    /hazards, /snc_status
```

---

## 🔩 Parameters

| Parameter | Default | คำอธิบาย |
|-----------|---------|----------|
| `objects_path` | `/path/to/objects_example` | โฟลเดอร์รูปป้ายที่ฝึกไว้ |
| `image_topic` | `/oak/rgb/image_raw/compressed` | Topic กล้อง |
| `use_compressed` | `true` | ภาพเป็น compressed หรือไม่ |
| `hfov_deg` | `69.0` | Horizontal FOV ของกล้อง (degrees) |
| `image_width` | `640.0` | ความกว้างภาพ (pixels) |
| `duplicate_threshold` | `0.5` | ระยะ (เมตร) สำหรับตัดป้ายซ้ำ |
| `confirm_frames` | `3` | จำนวน frame ก่อน confirm |
| `publish_rate` | `1.0` | อัตรา republish hazards (Hz) |
| `gui` | `false` | เปิด GUI ของ find_object_2d |
| `use_sim_time` | `true` | ใช้ sim clock (Gazebo) หรือ wall clock |

> ⚠️ **สำคัญ:** ตั้ง `use_sim_time:=false` เมื่อรันบนหุ่นจริง

---

## 🏷️ Hazard Marker IDs

| ID | ชื่อ | ID | ชื่อ |
|----|------|----|------|
| 0 | Unknown | 7 | Oxidizer |
| 1 | Explosive | 8 | Organic Peroxide |
| 2 | Flammable Gas | 9 | Inhalation Hazard |
| 3 | Non-Flammable Gas | 10 | Poison |
| 4 | Dangerous When Wet | 11 | Radioactive |
| 5 | Flammable Solid | 12 | Corrosive |
| 6 | Spontaneously Combustible | 13 | *(Start Marker — ไม่ publish)* |

---

## 🐛 การ Debug

### ดู Topics ที่ Active

```bash
ros2 topic list
ros2 topic hz /objects           # ตรวจว่า find_object_2d ส่งข้อมูลไหม
ros2 topic echo /snc_status      # ดูสถานะ Node #2
ros2 topic echo /hazards         # ดู markers ที่ detect แล้ว
```

### ตรวจสอบ TF

```bash
ros2 run tf2_tools view_frames    # export TF tree เป็น PDF
ros2 run tf2_ros tf2_echo map base_link  # ดู transform แบบ live
```

### ดูใน RViz2

```bash
rviz2
# เพิ่ม:
# - Map         → topic: /map
# - Marker      → topic: /hazards
# - LaserScan   → topic: /scan
# - TF          (เพื่อดู robot frame)
```

### Inject /objects เทียม (ทดสอบโดยไม่ต้องมีป้าย)

```bash
# ทดสอบว่า TF และ publish ทำงานถูกต้อง
# object_id=1 (Explosive), bbox center x ≈ 320 (กลางภาพ)
ros2 topic pub --once /objects std_msgs/msg/Float32MultiArray \
  "data: [1.0, 640.0, 480.0, 1.0,0.0,320.0, 0.0,1.0,240.0, 0.0,0.0,1.0]"
```

### Issue?

| อาการ | สาเหตุ | วิธีแก้ |
|-------|--------|---------|
| `No objects loaded from path` | objects_path ผิด | ตรวจสอบ path และตั้งค่าใหม่ |
| `TF transform failed: extrapolation into the future` | use_sim_time ไม่ตรงกัน | ตั้ง `use_sim_time` ให้ตรงกับ Nav2 |
| `No objects detected` (ตลอดเวลา) | ไม่มีป้ายในกรอบกล้อง หรือ image_topic ผิด | ตรวจ topic กล้อง / วางป้ายตรงหน้า |
| `/hazards` ไม่มีข้อมูล | ต้องเห็นป้ายติดต่อกัน 3 frame | ให้หุ่นยนต์หยุดนิ่งตรงหน้าป้าย |
| TF warn ทุกครั้ง | SLAM ยังไม่มี map frame | รัน slam_toolbox ก่อน |

---

