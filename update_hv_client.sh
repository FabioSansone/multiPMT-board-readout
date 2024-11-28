SERVICE_NAME="client_hv.service"

echo "Stopping the service…"
systemctl stop "$SERVICE_NAME"

echo "Reloading systemd manager configuration…"
systemctl daemon-reload

echo "Enabling the service…"
systemctl enable "$SERVICE_NAME"

echo "Starting the service…"
systemctl start "$SERVICE_NAME"

echo "Checking the status of the service…"
systemctl status "$SERVICE_NAME"
