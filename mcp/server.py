from mcp.server.fastmcp import FastMCP

mcp = FastMCP("incident-log")

# in memory db
incidents = []


@mcp.tool()
def add_incident(title: str, severity: str):
    """log a new incident

    Args:
        title (str): short description of what broke
        severity (str): one of low, medium, high, critical
    """
    incident = {
        "id": len(incidents) + 1,
        "title": title,
        "severity": severity,
        "resolved": False,
    }
    incidents.append(incident)
    return f"logged incident #{incident['id']}: {title} ({severity})"


@mcp.tool()
def resolve_incident(incident_id: int) -> str:
    """Mark an incident as resolved.

    Args:
        incident_id: the id of the incident to resolve
    """
    for inc in incidents:
        if inc["id"] == incident_id:
            inc["resolved"] = True
            return f"Incident #{incident_id} marked resolved."
    return f"No incident with id {incident_id}"



import httpx

@mcp.tool()
def get_weather(city: str) -> str:
    """Get current weather for a city.

    Args:
        city: name of the city, e.g. "Bengaluru" or "London"
    """
    # 1. geocode the city name to lat/lon
    geo = httpx.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": city, "count": 1}
    ).json()

    if not geo.get("results"):
        return f"Could not find location: {city}"

    loc = geo["results"][0]
    lat, lon = loc["latitude"], loc["longitude"]

    # 2. fetch current weather for those coordinates
    weather = httpx.get(
        "https://api.open-meteo.com/v1/forecast",
        params={"latitude": lat, "longitude": lon, "current_weather": True}
    ).json()

    cw = weather["current_weather"]
    return f"Weather in {loc['name']}, {loc.get('country', '')}: {cw['temperature']}°C, wind {cw['windspeed']} km/h"

@mcp.resource("incidents://all")
def get_all_incidents() -> str:
    """return all logged incidents as text."""
    if not incidents:
        return "no incidents logged yet"
    lines = [
        f"#{i['id']} [{i['severity']}] {i['title']} - {'RESOLVED' if i['resolved'] else 'OPEN'}"
        for i in incidents
    ]

    return "\n".join(lines)


@mcp.prompt()
def triage_prompt() -> str:
    """a prompt template for triaging open incidents"""
    return "review all open incidents and suggest which one to fix first, and why."


if __name__ == "__main__":
    mcp.run()
