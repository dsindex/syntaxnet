$(document).ready(function() {
	var submitElem = $('#btnSubmit');
	if (submitElem) {
		submitElem.on('click', function() {
			$.ajax({
				url: '/dragnntest',
				data: $('#docForm').serialize(),
				method: 'POST'
			}).done(function(data) {
				if (data.success) {
					if(data.filename) {
						d = new Date();
						$('#graph').attr('src', data.filename + "?" + d.getTime());
					}
					$('#info').empty();
					if(data.info) {
						$('textarea#info').text(data.info);
					}
					nbest = data.nbest;
					$('#record_table').empty();
					if(data.record) {
						var trHTML = '';
						trHTML += "<tr class=\"success\">";
						trHTML += "<th>A</th>";
						trHTML += "<th>B</th>";
						trHTML += "<th>C</th>";
						trHTML += "</tr>";
						$('#record_table').append(trHTML);
					}
				}
			});
		});
	}
});
