from flask import Flask, render_template, redirect, url_for, jsonify
import RPi.GPIO as GPIO
import paho.mqtt.client as mqtt
import dht11
import threading
import time

app = Flask(_name_)

# GPIO pin configuration
led1 = 21
led2 = 20
ledComb = 16
relay_pin = 23
dht11_data_pin = 10

# GPIO setup
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(led1, GPIO.OUT)
GPIO.setup(led2, GPIO.OUT)
GPIO.setup(ledComb, GPIO.OUT)
GPIO.setup(relay_pin, GPIO.OUT)

GPIO.output(led1, 0)
GPIO.output(led2, 0)
GPIO.output(ledComb, 0)
GPIO.output(relay_pin, GPIO.HIGH)  # Fan off by default

print("GPIO setup done")

# Device states
device_states = {
    "led1": "OFF",
    "led2": "OFF",
    "ledComb": "OFF",
    "fan1": "OFF",
    "autoFan": "OFF"
}

# MQTT setup
mqtt_broker = "localhost"
mqtt_port = 1883
mqtt_topic_led1 = "home/led1"
mqtt_topic_led2 = "home/led2"
mqtt_topic_ledComb = "home/ledComb"
mqtt_topic_fan1 = "home/fan1"
mqtt_topic_autoFan = "home/autoFan"

dht11_sensor_data = dht11.DHT11(pin=dht11_data_pin)

client = mqtt.Client(protocol=mqtt.MQTTv5)

# Auto Fan thread control
auto_fan_running = False

# Define callback functions for handling subscribed messages
def on_message(client, userdata, message):
    global auto_fan_running
    if message.topic == mqtt_topic_led1:
        if message.payload.decode() == "ON":
            GPIO.output(led1, 1)
            device_states["led1"] = "ON"
        elif message.payload.decode() == "OFF":
            GPIO.output(led1, 0)
            device_states["led1"] = "OFF"
    elif message.topic == mqtt_topic_led2:
        if message.payload.decode() == "ON":
            GPIO.output(led2, 1)
            device_states["led2"] = "ON"
        elif message.payload.decode() == "OFF":
            GPIO.output(led2, 0)
            device_states["led2"] = "OFF"
    elif message.topic == mqtt_topic_ledComb:
        if message.payload.decode() == "ON":
            GPIO.output(ledComb, 1)
            device_states["ledComb"] = "ON"
        elif message.payload.decode() == "OFF":
            GPIO.output(ledComb, 0)
            device_states["ledComb"] = "OFF"
    elif message.topic == mqtt_topic_fan1:
        if message.payload.decode() == "ON":
            GPIO.output(relay_pin, GPIO.LOW)
            device_states["fan1"] = "ON"
        elif message.payload.decode() == "OFF":
            GPIO.output(relay_pin, GPIO.HIGH)
            device_states["fan1"] = "OFF"
    elif message.topic == mqtt_topic_autoFan:
        if message.payload.decode() == "ON":
            device_states["autoFan"] = "ON"
            auto_fan_running = True
            threading.Thread(target=auto_fan_control).start()
        elif message.payload.decode() == "OFF":
            device_states["autoFan"] = "OFF"
            auto_fan_running = False

# Auto Fan control logic
def auto_fan_control():
    global auto_fan_running
    while auto_fan_running:
        values = dht11_sensor_data.read()
        if values.is_valid():
            temperature = values.temperature
            print(f"Temperature reading: {temperature}' C")  # Debug log for temperature
            if temperature >= 30 and auto_fan_running:
                GPIO.output(relay_pin, GPIO.LOW)  # Turn fan on
                device_states["fan1"] = "ON"
                print("Fan turned ON due to high temperature")
            elif temperature < 30 and auto_fan_running:
                GPIO.output(relay_pin, GPIO.HIGH)  # Turn fan off
                device_states["fan1"] = "OFF"
                print("Fan turned OFF due to LOW temperature")
        else:
            print("Failed to read from DHT11 sensor.")  # Debug log for sensor issues
        time.sleep(2)

# Set up MQTT client to subscribe to the topics
client.on_message = on_message
client.connect(mqtt_broker, mqtt_port, 60)
client.subscribe(mqtt_topic_led1)
client.subscribe(mqtt_topic_led2)
client.subscribe(mqtt_topic_ledComb)
client.subscribe(mqtt_topic_fan1)
client.subscribe(mqtt_topic_autoFan)

# Start MQTT client loop in a separate background thread
client.loop_start()

#  Flask Routes
@app.route("/")
def index():
    return render_template("index3.html", states=device_states)

@app.route("/A", methods=["POST"])
def led1on():
    client.publish(mqtt_topic_led1, "ON")
    return jsonify({"status": "ON"})

@app.route("/a", methods=["POST"])
def led1off():
    client.publish(mqtt_topic_led1, "OFF")
    return jsonify({"status": "OFF"})

@app.route("/B", methods=["POST"])
def led2on():
    client.publish(mqtt_topic_led2, "ON")
    return jsonify({"status": "ON"})

@app.route("/b", methods=["POST"])
def led2off():
    client.publish(mqtt_topic_led2, "OFF")
    return jsonify({"status": "OFF"})
@app.route("/C", methods=["POST"])
def ledCombon():
    client.publish(mqtt_topic_ledComb, "ON")
    return jsonify({"status": "ON"})

@app.route("/c", methods=["POST"])
def ledComboff():
    client.publish(mqtt_topic_ledComb, "OFF")
    return jsonify({"status": "OFF"})

@app.route("/F", methods=["POST"])
def fan1on():
    client.publish(mqtt_topic_fan1, "ON")
    return jsonify({"status": "ON"})

@app.route("/f", methods=["POST"])
def fan2off():
    client.publish(mqtt_topic_fan1, "OFF")
    return jsonify({"status": "OFF"})

@app.route("/setAutoFan/<status>")
def set_auto_fan(status):
    global auto_fan_running
    if status in ["ON", "OFF"]:
        client.publish(mqtt_topic_autoFan, status)
        auto_fan_running = (status == "ON")
        return jsonify({"autoFan": status})
    return jsonify({"error": "Invalid status"}), 400

@app.route("/getTemperature")
def get_dht11_sensor_data():
    values = dht11_sensor_data.read()
    if values.is_valid():
        return jsonify({"temperature": values.temperature, "humidity": values.humidity})
    return jsonify({"error": "wait for 2 sec...."})

# Start the Flask application
if _name_ == "_main_":
    app.run(host='192.168.37.40', port=5065)