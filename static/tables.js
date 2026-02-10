$(document).ready(function () {
	$('#summary').DataTable({
		"pageLength": 100,
		"paging": false,
		"searching": false,
		"info": false,
		"order": [[4, "desc"]],

		"columnDefs": [
			{
				"targets": [5, 7, 8, 10],
				"render": $.fn.dataTable.render.number(',', '.', 0, '$')
			},
			{
				"targets": [2, 6],
				"render": $.fn.dataTable.render.number(',', '.', 2, '$')
			},
			{
				"targets": [4, 9, 11, 12, 13, 14, 15],
				"render": $.fn.dataTable.render.number(',', '.', 2, '', '%'),
				"createdCell": function (td, cellData, rowData, row, col) {
					var val = parseFloat(cellData);
					if (val > 0) {
						$(td).css('color', 'green');
					} else if (val < 0) {
						$(td).css('color', 'red');
					}
				}
			},
			{
				"targets": [11, 12, 13, 14, 15],
				"defaultContent": "N/A"
			}
		]
	});
});
