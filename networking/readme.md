#  Complete Networking Protocol Hierarchy — TCP/IP, HTTP, DHCP, SMTP, POP3, IMAP, SSH, Telnet, MAC

A system-level explanation of how networking protocols fit together inside the TCP/IP architecture.

---

#  Core Principle: Layered Networking

Networking uses layered abstraction.

Each layer:
- solves a specific problem
- hides internal complexity
- communicates only with adjacent layers

Data Flow:

Sending:
```
Application → Transport → Internet → Link → Physical Wire
```

Receiving:
```
Physical Wire → Link → Internet → Transport → Application
```

---

#  TCP/IP Model — Full Flowchart

```
┌──────────────────────────────────────────────────────────┐
│                    APPLICATION LAYER                     │
│               (Meaning of communication)                 │
│                                                          │
│  HTTP   → Web traffic / APIs                             │
│  SMTP   → Send email                                     │
│  POP3   → Download email                                 │
│  IMAP   → Email synchronization                          │
│  SSH    → Secure remote login                            │
│  Telnet → Insecure remote login                          │
│  DHCP   → Automatic IP configuration                     │
└──────────────────────────▲───────────────────────────────┘
                           │ uses
                           │
┌──────────────────────────┴───────────────────────────────┐
│                    TRANSPORT LAYER                       │
│              (Process-to-process delivery)               │
│                                                          │
│  TCP → Reliable, ordered communication                   │
│  UDP → Fast, connectionless communication                │
│                                                          │
│                ✔ Part of TCP/IP stack                    │
└──────────────────────────▲───────────────────────────────┘
                           │ encapsulated inside
                           │
┌──────────────────────────┴───────────────────────────────┐
│                     INTERNET LAYER                       │
│               (Logical addressing & routing)             │
│                                                          │
│  IP (IPv4 / IPv6) → Packet routing                       │
│  ICMP → Errors & diagnostics                             │
│                                                          │
│                ✔ Part of TCP/IP stack                    │
└──────────────────────────▲───────────────────────────────┘
                           │ transmitted via
                           │
┌──────────────────────────┴───────────────────────────────┐
│             NETWORK ACCESS / LINK LAYER                  │
│                (Local network delivery)                  │
│                                                          │
│  Ethernet                                                │
│  Wi-Fi                                                   │
│  ARP                                                     │
│  MAC Addressing                                          │
└──────────────────────────────────────────────────────────┘
```

---

#  What is TCP/IP?

Originally:
- TCP — Transmission Control Protocol
- IP — Internet Protocol

Modern meaning:

> TCP/IP = the entire Internet protocol suite.

It defines how machines communicate across networks.

---

## TCP/IP Coverage

| Layer | Included in TCP/IP |
|---|---|
| Application | Yes (conventionally) |
| Transport | Yes |
| Internet | Yes |
| Link | Yes |

---

# 🔎 Protocol Classification

## Application Layer

Defines meaning of communication.

| Protocol | Purpose | Transport |
|---|---|---|
| HTTP | Web requests | TCP |
| SMTP | Send email | TCP |
| POP3 | Retrieve email | TCP |
| IMAP | Sync email | TCP |
| SSH | Secure shell | TCP |
| Telnet | Remote shell (plaintext) | TCP |
| DHCP | Assign IP address | UDP |

---

## Transport Layer

Provides process-to-process communication.

### TCP
Features:
- Reliable delivery
- Ordering
- Retransmission
- Flow control
- Congestion control

Used by:
HTTP, SMTP, SSH, IMAP, POP3.

### UDP
Features:
- No connection setup
- No guarantees
- Low latency

Used by:
DHCP, DNS, streaming systems.

---

## Internet Layer

### IP Responsibilities
- Logical addressing
- Routing packets
- Fragmentation

Property:
Best-effort delivery.

Routers operate here.

---

## Link Layer

Handles local delivery.

### MAC Address
Hardware identifier of network interface.

Example:
```
00:1A:2B:3C:4D:5E
```

Switches forward using MAC addresses.

---

# 📡 Encapsulation

Each layer wraps data:

```
Application Data
      ↓
[TCP Header + Data] → Segment
      ↓
[IP Header + Segment] → Packet
      ↓
[MAC Header + Packet] → Frame
      ↓
Bits on wire
```

Receiving reverses the process.

---

#  Real Example — Opening a Website

```
1. DHCP assigns IP
2. DNS resolves domain
3. TCP handshake
4. TLS encryption
5. HTTP request/response
```

Stack view:

```
HTTP
 ↓
TCP
 ↓
IP
 ↓
Ethernet/Wi-Fi
```

---

#  TCP 3-Way Handshake

```
Client → SYN →
Server → SYN-ACK →
Client → ACK →
Connection Established
```

Purpose:
- sequence sync
- reliability negotiation

---

# ⚠️ Common Confusions

## TCP/IP vs HTTP

| TCP/IP | HTTP |
|---|---|
| Moves data | Defines meaning |

---

## SSH vs Telnet

| SSH | Telnet |
|---|---|
| Encrypted | Plaintext |
| Secure | Insecure |

---

## POP3 vs IMAP

| POP3 | IMAP |
|---|---|
| Downloads mail | Syncs mail |
| Single device | Multi-device |

---

## MAC vs IP

| MAC | IP |
|---|---|
| Physical identity | Logical identity |
| Local | Global |

Routers change MAC headers at every hop.
IP remains end-to-end.

---

#  Mental Model

```
Application → Talks
Transport   → Guarantees
Internet    → Routes
Link        → Local delivery
```

---

#  Production Debugging Mapping

| Symptom | Likely Layer |
|---|---|
| Cannot connect | TCP |
| Packet loss | IP/network |
| Wrong response | Application |
| No IP assigned | DHCP |
| SSH timeout | Transport/firewall |

Debug from top → downward.

---

# ⚙️ High-Level Linux Packet Path

Outgoing request:

```
Application (FastAPI)
 → Socket API
 → Kernel TCP stack
 → IP layer
 → NIC driver
 → Network card
 → Wire
```

Incoming reverses this path.

---

#  One-Line Summary

```
HTTP uses TCP
TCP uses IP
IP uses MAC/Ethernet
```

Full chain:

```
Application → TCP/UDP → IP → MAC → Physical Network
```

---
