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
					if(data.pgraph) {
						setTimeout( function() {
							var iframe = $('#pgraph');
							var doc = iframe[0].contentWindow.document;
							var body = $('body',doc);
							body.html(data.pgraph);
						}, 1 );
					}
					$('#info').empty();
					if(data.info) {
						$('textarea#info').text(data.info);
					}
					$('#record_table').empty();
					if(data.record) {
						var trHTML = '';
						trHTML += "<tr class=\"success\">";
						trHTML += "<th>id</th>";
						trHTML += "<th>form</th>";
						trHTML += "<th>lemma</th>";
						trHTML += "<th>upostag</th>";
						trHTML += "<th>xpostag</th>";
						trHTML += "<th>feats</th>";
						trHTML += "<th>head</th>";
						trHTML += "<th>deprel</th>";
						trHTML += "<th>deps</th>";
						trHTML += "<th>misc</th>";
						trHTML += "</tr>";
						$.each(data.record, function (i, entry) {
							$.each(entry, function (j, item) {
								trHTML += '<tr><td>' + item.id;
								if( item.head == '0' ) item.form = '<font color=Blue>' + item.form + '</font>';
								trHTML += '</td><td>' + item.form;
								trHTML += '</td><td>' + item.lemma;
								trHTML += '</td><td>' + item.upostag;
								trHTML += '</td><td>' + item.xpostag;
								trHTML += '</td><td>' + item.feats;
								trHTML += '</td><td>' + item.head;
								trHTML += '</td><td>' + item.deprel;
								trHTML += '</td><td>' + item.deps;
								trHTML += '</td><td>' + item.misc;
								trHTML += '</td></tr>';
							});
							trHTML += '<tr></tr>';
						});
						$('#record_table').append(trHTML);
					}
				}
			});
		});
	}
});
