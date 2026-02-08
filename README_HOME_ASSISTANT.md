# Home Assistant Integration for Carman Power Consumption

This integration allows you to monitor your Carman Smart Metering power consumption data in Home Assistant.

## Features

- Real-time power consumption monitoring
- Historical data visualization
- Cost calculations
- Automated daily updates
- REST API for data access
- Docker support

## Setup Instructions

### 1. Install Requirements

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Edit `.env` file with your credentials:
```
USERNAME=your_meter_username
PASSWORD=your_meter_password
```

### 3. Initial Data Collection

Run the scraper to collect historical data:
```bash
python carman_scraper.py --months 12
```

### 4. Start the API Server

#### Option A: Direct Python
```bash
python home_assistant_api.py
```

#### Option B: Docker Compose
```bash
docker-compose up -d
```

The API will be available at `http://YOUR_SERVER_IP:5000`

### 5. Configure Home Assistant

1. **Add REST sensors** to `configuration.yaml`:
   - Copy the contents of `home_assistant_config.yaml`
   - Replace `YOUR_SERVER_IP` with your server's IP address
   - Adjust electricity rate (default $0.12/kWh)

2. **Add Lovelace Dashboard**:
   - Go to Settings → Dashboards
   - Create new dashboard
   - Edit in YAML mode
   - Paste contents of `lovelace_dashboard.yaml`

3. **Restart Home Assistant** to load new sensors

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/status` | Check API status and database info |
| `GET /api/current` | Get today's and yesterday's consumption |
| `GET /api/daily/<date>` | Get consumption for specific date |
| `GET /api/monthly/<year>/<month>` | Get monthly summary |
| `GET /api/range?start=<date>&end=<date>` | Get range of dates |
| `GET /api/statistics` | Get overall statistics |
| `POST /api/update` | Trigger data update |

## Home Assistant Entities Created

### Sensors
- `sensor.power_consumption_today` - Today's consumption (kWh)
- `sensor.power_consumption_yesterday` - Yesterday's consumption (kWh)
- `sensor.power_consumption_month_total` - Current month total (kWh)
- `sensor.power_meter_reading` - Latest meter reading
- `sensor.power_consumption_stats` - Statistical data
- `sensor.power_daily_average_this_month` - Monthly daily average
- `sensor.power_consumption_trend` - Consumption trend indicator
- `sensor.power_cost_today` - Today's cost estimate
- `sensor.power_cost_this_month` - Month's cost estimate

### Automations
- Daily automatic data update at 12:30 AM

### Utility Meters
- Daily, weekly, and monthly consumption tracking

### Input Numbers
- `input_number.power_daily_target` - Set daily consumption target
- `input_number.power_high_usage_threshold` - High usage alert threshold

## Dashboard Features

1. **Overview Tab**:
   - Real-time gauges for today, yesterday, and monthly consumption
   - 7-day statistics
   - Cost tracking
   - Consumption trend
   - 7-day history graph

2. **Detailed Stats Tab**:
   - Complete statistics
   - Record high/low days
   - Monthly comparison chart
   - Manual update button

3. **Energy Dashboard Tab**:
   - Integration with Home Assistant Energy Dashboard

## Customization

### Adjust Update Interval
Edit `docker-compose.yml` or set environment variable:
```yaml
UPDATE_INTERVAL=1800  # Update every 30 minutes
```

### Change Electricity Rate
Edit in `home_assistant_config.yaml`:
```yaml
{% set rate = 0.15 %}  # Your rate per kWh
```

### Modify Alert Thresholds
Use Home Assistant UI to adjust:
- Daily power target
- High usage threshold

## Troubleshooting

1. **No data showing**:
   - Check API is running: `http://YOUR_SERVER_IP:5000/api/status`
   - Verify database has data: `python query_power_data.py --summary`
   - Check Home Assistant logs

2. **Update not working**:
   - Check .env credentials are correct
   - Verify scraper works: `python carman_scraper.py --months 1`
   - Check API logs: `docker-compose logs`

3. **High memory usage**:
   - Increase update interval
   - Limit historical data collection

## Security Notes

- Keep API behind firewall/VPN
- Don't expose port 5000 to internet
- Use Home Assistant's authentication
- Store credentials securely in .env

## Advanced Features

### Custom REST Commands
```yaml
rest_command:
  get_specific_month:
    url: "http://YOUR_SERVER_IP:5000/api/monthly/{{ year }}/{{ month }}"
    method: GET
```

### Template Sensors for Analysis
```yaml
template:
  - sensor:
    - name: "Power Usage vs Target"
      unit_of_measurement: "%"
      state: >
        {% set current = states('sensor.power_consumption_today') | float(0) %}
        {% set target = states('input_number.power_daily_target') | float(30) %}
        {{ ((current / target) * 100) | round(1) }}
```

### Notifications
```yaml
automation:
  - alias: "High Power Usage Alert"
    trigger:
      platform: numeric_state
      entity_id: sensor.power_consumption_today
      above: input_number.power_high_usage_threshold
    action:
      service: notify.mobile_app
      data:
        title: "High Power Usage"
        message: "Today's consumption: {{ states('sensor.power_consumption_today') }} kWh"
```

## Support

For issues or questions:
1. Check API status endpoint
2. Review logs: `docker-compose logs`
3. Verify database: `python query_power_data.py --all`