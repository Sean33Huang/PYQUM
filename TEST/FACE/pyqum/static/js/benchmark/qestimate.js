


$(document).ready(function(){
    // $('div.qestimatecontent').show();
    render_selection("qEstimation");
    console.log( "Load qEstimation" );
    $('#qFactor-fit-button').hide();
});

// saving exported mat-data to client's PC:
$('#qFactor-Download-button').on('click', function () {
    console.log("SAVING CSV FILE");

    $.getJSON( '/benchmark/qestimate/exportMat_fitPara', {
    }, function (data) {
        console.log("STATUS: " + data.status + ", PORT: " + data.qumport);
        $.ajax({
            url: 'http://qum.phys.sinica.edu.tw:' + data.qumport + '/mach/uploads/ANALYSIS/QEstimation[' + data.user_name + '].mat',
            method: 'GET',
            xhrFields: {
                responseType: 'blob'
            },
            success: function (data) {
                console.log("USER HAS DOWNLOADED QEstimation DATA from " + String(window.URL));
                var a = document.createElement('a');
                var url = window.URL.createObjectURL(data);
                a.href = url;
                a.download = 'QEstimation.mat';
                document.body.append(a);
                a.click();
                a.remove();
                window.URL.revokeObjectURL(url);
                //$('#qFactor-Download-button').hide();
            }
        });
    });
    return false;
});

//Just for test
$('#qFactor-test-button').on('click', function () {
    $.getJSON( '/benchmark/test',{  

    }, function (data) {
        console.log( data )
    });

});

// plot
$('#qFactor-plot-button').on('click', function () {
    $('div.qestimate#qestimate-fitting-progress').empty().append($('<h4 style="color: blue;"></h4>').text("PLOTTING RELEVANT DATA..."));
    let plotID_2D = "qFactor-plot2D-rawOverview";
    let plotID_1D_ampPhase = "qFactor-plot1D-ampPhase";
    let plotID_1D_IQ = "qFactor-plot1D-IQ";
    console.log( "plot!!" );
    $.ajaxSettings.async = false;
    let htmlInfo=get_htmlInfo_python();
    let analysisIndex = get_selectInfo("qEstimation");
    if ( analysisIndex.axisIndex.length == 2 ) {
        $.getJSON( '/benchmark/qestimate/getJson_plot',
        {   quantificationType: JSON.stringify("qEstimation"), 
            analysisIndex: JSON.stringify(analysisIndex), 
            plotType: JSON.stringify("2D_amp"), },
            function (data) {
            console.log( "2D plot" );
            console.log( data );
            let axisKeys = {
                x: htmlInfo[analysisIndex.axisIndex[0]]["name"],
                y: htmlInfo[analysisIndex.axisIndex[1]]["name"],
                z: "amplitude",
            }
            console.log( data );
            
            document.getElementById(plotID_2D).style.display = "block";
            plot2D(data, axisKeys, plotID_2D);
        })
        .done(function(data) {
            $('#qFactor-fit-button').show();
            $('div.qestimate#qestimate-fitting-progress').empty().append($('<h4 style="color: blue;"></h4>').text("DATA-PLOT COMPLETE"));
        })
        .fail(function(jqxhr, textStatus, error){
            $('div.qestimate#qestimate-fitting-progress').empty().append($('<h4 style="color: red;"></h4>').text("Oops.. Something went wrong!"));
        });

    } else {
        document.getElementById(plotID_2D).style.display = "none";
    };

    $.getJSON( '/benchmark/qestimate/getJson_plot',
    {   quantificationType: JSON.stringify("qEstimation"), 
        analysisIndex: JSON.stringify(analysisIndex),
        plotType: JSON.stringify("1D_all"), },
        function (data) {
        console.log( "1D plot test Q" );
        console.log( data );
        let ampPhaseKeys = {
            x: [ [htmlInfo[analysisIndex.axisIndex[0]]["name"]], [htmlInfo[analysisIndex.axisIndex[0]]["name"]] ] ,
            y: [ ["Amplitude"],["Phase"] ],
            yErr: [ [],[] ],
        }
        plot1D_2subplot_shareX(data, ampPhaseKeys, plotID_1D_ampPhase);
        
        let iqKeys = {
            x: [["I"]],
            y: [["Q"]],
            yErr: [[]],
        }
        plot1D_2y(data, iqKeys, plotID_1D_IQ);
    })
    .done(function(data) {
        $('#qFactor-fit-button').show();
        $('div.qestimate#qestimate-fitting-progress').empty().append($('<h4 style="color: blue;"></h4>').text("FITTED IQ-PLOT COMPLETE"));
    })
    .fail(function(jqxhr, textStatus, error){
        $('div.qestimate#qestimate-fitting-progress').empty().append($('<h4 style="color: red;"></h4>').text("Oops.. Something went wrong!"));
    });

    $.ajaxSettings.async = true;
    return false;
});

//Test fit data
$('#qFactor-fit-button').on('click', function () {
    $('div.qestimate#qestimate-fitting-progress').empty().append($('<h4 style="color: blue;"></h4>').text("PLOTTING FITTED PARAMETERS"));

    $.ajaxSettings.async = false;
    let htmlInfo=get_htmlInfo_python();
    let analysisIndex = get_selectInfo("qEstimation");

    console.log( "Fit plot" );
    console.log( analysisIndex );

    let xAxisKey = htmlInfo[analysisIndex["axisIndex"][0]]["name"];
    let fitRange = document.getElementById("qEstimation"+"-fitting_input-"+xAxisKey).value;

    let baseline_correction = document.getElementById("qFactor-fit-baseline-correct").checked;
    let baseline_smoothness = document.getElementById("qFactor-fit-baseline-smoothness").value;
    let baseline_asymmetry = document.getElementById("qFactor-fit-baseline-asymmetry").value;
    let gain = document.getElementById("qFactor-fit-gain").value;

    let fitParameters = {
        interval: {
            input: fitRange,
        },
        baseline:{
            correction: baseline_correction,
            smoothness: baseline_smoothness,
            asymmetry: baseline_asymmetry,
        },
        gain:gain,
        
    }
    
    console.log(fitParameters);

    // Plot fit parameters
    $.getJSON( '/benchmark/qestimate/getJson_fitParaPlot',{  
        fitParameters: JSON.stringify(fitParameters),
        analysisIndex: JSON.stringify(analysisIndex), 
    }, function (data) {
        console.log("fitResult");
        console.log(data);
        let fitResultxAxisKey = "Single_plot";

        if (analysisIndex.axisIndex.length == 2) { fitResultxAxisKey = htmlInfo[analysisIndex["axisIndex"][1]]["name"] }
        // if ( fitResultxAxisKey == "Power" ) { fitResultxAxisKey = "power_corr" }

        console.log("xAxisKey: "+fitResultxAxisKey);

        let axisKeys_fitResult = {
            x: [fitResultxAxisKey],
            y: ["Qi_dia_corr","Qi_no_corr","absQc","Qc_dia_corr","Ql","fr","theta0","phi0","single_photon_limit", "photons_in_resonator"],
            yErr: ["Qi_dia_corr_err", "Qi_no_corr_err", "absQc_err", "absQc_err", "Ql_err", "fr_err", "", "phi0_err","",""],
        }
        let plotdata = Object.assign({}, data["extendResults"], data["results"], data["errors"] );
        plotdata[fitResultxAxisKey] = data[fitResultxAxisKey]
        plot1D( plotdata, axisKeys_fitResult, "qFactor-plot-fittingParameters");

    })
    .done(function(data) {
        // $('#qFactor-fit-button').show();
        $('div.qestimate#qestimate-fitting-progress').empty().append($('<h4 style="color: blue;"></h4>').text("Q-FITTING COMPLETE"));
    })
    .fail(function(jqxhr, textStatus, error){
        $('div.qestimate#qestimate-fitting-progress').empty().append($('<h4 style="color: red;"></h4>').text("Oops.. Something went wrong!"));
    });

    $.ajaxSettings.async = true;
    return false;
});



