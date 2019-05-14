$(function(){
	// checkbox select all or cancel all
	$("input[name='checkall']").click(function(){
		if(this.checked){
			$("input[name='cc']").prop("checked", true);  
		}else{   
			$("input[name='cc']").prop("checked", false);
					}
	});

	$("input[name='confirm_task']").click(function(){
		var result = gether_table();
		$("#hidTD").val(JSON.stringify(result));
		$("#form").submit();
	});

	$("input[name='update_waitlist']").click(function(){
		var result = gether_checkbox();
		$("#hidTD").val(JSON.stringify(result));
		$("#form").submit();
	});

})

// function update_waitlist(){
	  // record all checkbox val
		// var all = [];
		// $("input:checkbox").each(function() {
		// 		all.push($(this).attr("value"));
		// });

		// addup checked values
// 		var che = [];
// 		$("input[name='cc']:checked").each(function() {
// 				che.push({"11":$(this).val()});
// 		});
// 		alert(che)
// 		// post result
// 		$.post("/dashboard/waitlist",{wailist:che});

// 		//remove checked
// 		$("input:checkbox").each(function() {
// 			$(this).prop("checked", false);
// 		});
// 		alert("added to waitlist");
// }

function remove_from_waitlist(obj){
	var tr = obj.parentNode.parentNode;
	var tds = $(tr).find("td");
	$.post("/dashboard/waitlist", {delete:$(tds[0]).html()});
	tr.parentNode.removeChild(tr);
}

function gether_table(){
	var tr = $("#table tr");
	var result = [];
	
	for (var i=1; i<tr.length; i++){
		var tds = $(tr[i]).find("td");
		if (tds.length>0){
			result.push($(tds[0]).html());
		}
	}
	return result
}

function gether_checkbox(){
	var check = $("input[name=cc]:checked");
	var result = [];
	check.each(function(){
		var row = $(this).parent("td").parent("tr");//获取当前行
		var tds = $(row).find("td");
		result.push($(tds[1]).html());
	})
	return result
}