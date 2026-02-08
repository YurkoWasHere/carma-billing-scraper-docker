# Carman Smart Metering Power Consumption Scraper

A Python-based scraper for Carman Smart Metering portal that collects power consumption data and integrates with Home Assistant for real-time monitoring and analysis.

## 🚀 Features

- **Automated Data Collection**: Scrape daily power consumption data from Carman Smart Metering portal
- **Historical Data**: Collect up to 20 years of historical consumption data
- **SQLite Database**: Local storage of all consumption data
- **Home Assistant Integration**: REST API for real-time monitoring
- **Smart Navigation**: Handles ASP.NET postbacks and server errors
- **Rate Limiting**: Configurable pauses to prevent server overload
- **Docker Support**: Easy deployment with Docker Compose

## 📋 Requirements

- Python 3.8+
- Carman Smart Metering account credentials
- Home Assistant (optional, for integration)

## 🛠️ Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/carman-power-scraper.git
cd carman-power-scraper
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure credentials:
```bash
cp .env.example .env
# Edit .env with your credentials
```

## ⚙️ Configuration

Create a `.env` file with your credentials:
```env
USERNAME=your_meter_number
PASSWORD=your_password
```

## 🏃 Usage

### Basic Scraping

#### Collect current month data:
```bash
python carman_scraper.py --months 1
```

#### Collect historical data (with pauses):
```bash
python carman_scraper.py --months 240 --pause-interval 6 --pause-duration 30
```

#### Options:
- `--months N`: Number of months to go back (default: 12)
- `--pause-interval N`: Pause every N months (default: 6)
- `--pause-duration S`: Pause duration in seconds (default: 30)
- `--no-stop`: Don't stop on empty months
- `--db PATH`: Custom database path

### Query Data

```bash
# View monthly summaries
python query_power_data.py --summary

# View all data
python query_power_data.py --all

# View highest/lowest consumption days
python query_power_data.py --extremes

# View specific date range
python query_power_data.py --daily --start 2025-01-01 --end 2025-01-31
```

## 🏠 Home Assistant Integration

### Quick Start

1. **Start the API server**:
```bash
# Direct Python
python home_assistant_api.py

# Or with Docker
docker-compose up -d
```

2. **Add to Home Assistant**:
   - Copy `home_assistant_config.yaml` content to your `configuration.yaml`
   - Replace `YOUR_SERVER_IP` with your server IP
   - Restart Home Assistant

3. **Import Dashboard**:
   - Go to Settings → Dashboards
   - Create new dashboard
   - Edit in YAML mode
   - Paste `lovelace_dashboard.yaml` content

### API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/status` | API status and database info |
| `GET /api/current` | Today's and yesterday's consumption |
| `GET /api/daily/<date>` | Specific date consumption |
| `GET /api/monthly/<year>/<month>` | Monthly summary |
| `GET /api/statistics` | Overall statistics |
| `POST /api/update` | Trigger data update |

### Features in Home Assistant

- **Real-time Monitoring**: Today's, yesterday's, and monthly consumption
- **Cost Tracking**: Automatic electricity cost calculations
- **Trend Analysis**: Consumption trend indicators
- **Alerts**: High usage notifications
- **Graphs**: Historical consumption visualization
- **Statistics**: Min/max/average consumption data
- **Automated Updates**: Scrapes new data daily at 5 AM (configurable)
- **Database-First**: All queries served from local SQLite database for instant response

## 🐳 Docker Deployment

### Option 1: Use Pre-built Image (Recommended)

```bash
# Set your GitHub repository name
export GITHUB_REPOSITORY=yourusername/carman-power-scraper

# Use the pre-built image
docker-compose -f docker-compose.ghcr.yml up -d
```

### Option 2: Build Locally

```bash
# Build and run locally
docker-compose up -d
```

This will:
- Start the API server on port 5000
- Enable automatic daily updates at 5 AM
- Mount database as volume
- Use credentials from .env file

## 📊 Database Schema

The SQLite database contains:

- **daily_consumption**: Daily kWh consumption records
- **consumption_summary**: Monthly aggregated data
- **meter_readings**: Meter reading snapshots
- **scraping_history**: Track collection history

## 🔧 Advanced Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `USERNAME` | (required) | Your Carman meter number |
| `PASSWORD` | (required) | Your Carman password |
| `API_HOST` | 0.0.0.0 | API server host |
| `API_PORT` | 5000 | API server port |
| `DB_PATH` | power_consumption.db | Database file path |
| `AUTO_UPDATE` | true | Enable automatic daily updates |
| `UPDATE_HOUR` | 5 | Hour to run update (24-hour format) |

### Customization

- **Electricity Rate**: Edit rate in `home_assistant_config.yaml`
- **Alert Thresholds**: Configure via Home Assistant UI
- **Update Schedule**: Modify automation in HA config

## 📝 Project Structure

```
carman-power-scraper/
├── carman_scraper.py           # Main scraper with historical support
├── query_power_data.py          # Database query utility
├── home_assistant_api.py        # REST API server
├── home_assistant_config.yaml   # HA sensor configuration
├── lovelace_dashboard.yaml      # HA dashboard configuration
├── docker-compose.yml           # Docker deployment
├── Dockerfile                   # Container configuration
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment template
└── power_consumption.db         # SQLite database (auto-created)
```

## ⚠️ Important Notes

- **Security**: Keep API behind firewall/VPN, don't expose to internet
- **Credentials**: Store securely in `.env`, never commit to git
- **Rate Limiting**: Respect server limits with pause intervals
- **Server Errors**: Script handles 500 errors with retries

## 🐛 Troubleshooting

### No data showing in Home Assistant
1. Check API status: `http://YOUR_IP:5000/api/status`
2. Verify database has data: `python query_power_data.py --summary`
3. Check HA logs for errors

### Scraper fails with 500 errors
- Increase pause intervals
- Reduce number of months per run
- Check if portal is accessible manually

### Database issues
- Ensure write permissions: `chmod 664 power_consumption.db`
- Check disk space
- Verify SQLite version: `sqlite3 --version`

## 📈 Example Output

```
📅 Processing January 2026...
  Found 31 days of data
  Total: 959.28 kWh
  ✓ 31 new, 0 updated records

Monthly Summary:
  • January 2026: 959.28 kWh (30.94 kWh/day)
  • December 2025: 964.16 kWh (31.10 kWh/day)
  
Total consumption: 1923.44 kWh
```

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## 📄 License

MIT License - See LICENSE file for details

## 🙏 Acknowledgments

- Built for Carman Smart Metering portal
- Integrates with Home Assistant
- Uses Highcharts data extraction

## 📞 Support

For issues or questions:
1. Check the troubleshooting section
2. Review closed GitHub issues
3. Open a new issue with details

---

**Note**: This tool is for personal use with your own Carman Smart Metering account. Respect the service's terms of use and rate limits.