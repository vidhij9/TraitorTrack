/**
 * Basic QR Scanner - Absolutely minimal, guaranteed to work
 */

class BasicScanner {
    constructor(containerId, onSuccess) {
        this.container = document.getElementById(containerId);
        this.onSuccess = onSuccess;
        this.scanning = false;
        this.video = null;
        this.canvasElement = null;
        this.canvas = null;
        
        this.init();
    }
    
    init() {
        // Simple HTML structure
        this.container.innerHTML = `
            <div style="position:relative;">
                <video id="video" width="100%" style="border-radius:8px;"></video>
                <canvas id="canvas" hidden></canvas>
                <div id="output" style="margin-top:10px;">
                    <div id="outputMessage" style="background:#000;color:#0f0;padding:10px;border-radius:5px;text-align:center;">
                        Starting camera...
                    </div>
                    <div id="outputData" style="display:none;background:#0f0;color:#000;padding:10px;margin-top:10px;border-radius:5px;font-weight:bold;text-align:center;"></div>
                </div>
            </div>
        `;
        
        this.video = document.getElementById("video");
        this.canvasElement = document.getElementById("canvas");
        this.canvas = this.canvasElement.getContext("2d");
        this.outputMessage = document.getElementById("outputMessage");
        this.outputData = document.getElementById("outputData");
        
        // Start immediately
        this.startCamera();
    }
    
    startCamera() {
        // Use getUserMedia to access the camera
        navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } })
            .then((stream) => {
                this.video.srcObject = stream;
                this.video.setAttribute("playsinline", true); // required for iOS
                this.video.play();
                this.scanning = true;
                requestAnimationFrame(() => this.tick());
            })
            .catch((err) => {
                // Try without environment camera
                navigator.mediaDevices.getUserMedia({ video: true })
                    .then((stream) => {
                        this.video.srcObject = stream;
                        this.video.setAttribute("playsinline", true);
                        this.video.play();
                        this.scanning = true;
                        requestAnimationFrame(() => this.tick());
                    })
                    .catch((err2) => {
                        console.error("Camera error:", err2);
                        this.outputMessage.innerText = "Unable to access camera. Please check permissions.";
                        this.outputMessage.style.color = "#f00";
                    });
            });
    }
    
    tick() {
        if (!this.scanning) return;
        
        this.outputMessage.innerText = "⏳ Scanning for QR code...";
        
        if (this.video.readyState === this.video.HAVE_ENOUGH_DATA) {
            this.canvasElement.height = this.video.videoHeight;
            this.canvasElement.width = this.video.videoWidth;
            this.canvas.drawImage(this.video, 0, 0, this.canvasElement.width, this.canvasElement.height);
            
            var imageData = this.canvas.getImageData(0, 0, this.canvasElement.width, this.canvasElement.height);
            
            // Check if jsQR is loaded
            if (typeof jsQR !== 'undefined') {
                var code = jsQR(imageData.data, imageData.width, imageData.height, {
                    inversionAttempts: "dontInvert",
                });
                
                if (code) {
                    this.drawLine(code.location.topLeftCorner, code.location.topRightCorner, "#FF3B58");
                    this.drawLine(code.location.topRightCorner, code.location.bottomRightCorner, "#FF3B58");
                    this.drawLine(code.location.bottomRightCorner, code.location.bottomLeftCorner, "#FF3B58");
                    this.drawLine(code.location.bottomLeftCorner, code.location.topLeftCorner, "#FF3B58");
                    
                    this.outputMessage.style.display = "none";
                    this.outputData.style.display = "block";
                    this.outputData.innerText = "✅ Found: " + code.data;
                    
                    // Beep
                    try {
                        var audio = new Audio('data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBSuBzvLZiTYIG2m98OScTgwOUand7blmFgU7k9n1unEiBC13yO/eizEIHWq+8+OWT');
                        audio.play();
                    } catch(e) {}
                    
                    // Vibrate
                    if (navigator.vibrate) navigator.vibrate(200);
                    
                    // Call success callback
                    if (this.onSuccess) {
                        this.onSuccess(code.data);
                    }
                    
                    // Continue scanning after 2 seconds
                    setTimeout(() => {
                        this.outputMessage.style.display = "block";
                        this.outputData.style.display = "none";
                    }, 2000);
                }
            } else {
                this.outputMessage.innerText = "❌ jsQR library not loaded!";
                this.outputMessage.style.color = "#f00";
            }
        }
        
        requestAnimationFrame(() => this.tick());
    }
    
    drawLine(begin, end, color) {
        this.canvas.beginPath();
        this.canvas.moveTo(begin.x, begin.y);
        this.canvas.lineTo(end.x, end.y);
        this.canvas.lineWidth = 4;
        this.canvas.strokeStyle = color;
        this.canvas.stroke();
    }
    
    stop() {
        this.scanning = false;
        if (this.video && this.video.srcObject) {
            this.video.srcObject.getTracks().forEach(track => track.stop());
        }
    }
}

window.BasicScanner = BasicScanner;