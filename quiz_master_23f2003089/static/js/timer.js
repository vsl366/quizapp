document.addEventListener("DOMContentLoaded", function () {
    var timerElement = document.getElementById("timer");
    var form = document.getElementById("quiz-form");

    function updateTimer() {
        var minutes = Math.floor(duration / 60);
        var seconds = duration % 60;
        timerElement.textContent = `Time Left: ${minutes}:${seconds < 10 ? '0' : ''}${seconds}`;
        
        if (duration <= 0) {
            clearInterval(timerInterval);
            alert("Time's up! Submitting quiz...");
            form.submit();  // Auto-submit when time runs out
        } else {
            duration--;
        }
    }  

    var timerInterval = setInterval(updateTimer, 1000);
    updateTimer(); // Initialize immediately
});
