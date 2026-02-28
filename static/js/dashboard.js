document.addEventListener("DOMContentLoaded", function () {

const ctx = document.getElementById('txnChart');

new Chart(ctx, {
    type: 'doughnut',
    data: {
        labels: ['Deposit', 'Withdraw'],
        datasets: [{
            data: [5000, 2000],
            backgroundColor: ['#22c55e','#ef4444']
        }]
    }
});

const ctx2 = document.getElementById('monthlyChart');

new Chart(ctx2, {
    type: 'bar',
    data: {
        labels: ['Jan','Feb','Mar','Apr','May','Jun'],
        datasets: [{
            label: 'Transactions',
            data: [3,5,2,8,6,4],
            backgroundColor:'#1a73e8'
        }]
    }
});

});