$(document).ready( function () {
    $('#summary').DataTable({
		"pageLength": 100,
		"paging" : false,
		"searching" : false,
		"info" : false,
		"order": [[3, "desc" ]],

		"columnDefs": [
            {
				"targets": [5, 7, 8, 9],
				"render" : $.fn.dataTable.render.number( ',', '.', 0, '$' )
			},
            {
				"targets": [2, 6],
				"render" : $.fn.dataTable.render.number( ',', '.', 2, '$' )
			},
			{
				"targets" : [3],
				render: $.fn.dataTable.render.number(',', '.', 2, '', '%')
			}
		]
	});
});
