//--------------------Global functions-------------------------
// 開關深色模式
var dark = document.getElementById("dmbutton");
dark.addEventListener('click' , darkMode);
// Dark Mode
function darkMode() {
    let element = document.body;
    element.classList.toggle("dark-mode");
    if(document.getElementById('dmbutton').value=='0'){
        document.getElementById('dmbutton').setAttribute('value','1');
        //按鍵變為深色模式
        let but = document.getElementsByClassName('content-button');
        for(let i=0;i<but.length;i++){
            but[i].style.color = 'rgb(0,255,0)';
        };

    }else{
        document.getElementById('dmbutton').setAttribute('value','0');
        let but = document.getElementsByClassName('content-button');
        for(let i=0;i<but.length;i++){
            but[i].style.color = 'rgb(0,0,0)';
        };
    };
    dark_plot();
};

function dark_plot(){
    const ids=['CS-search','PD-search','FD-search','CW-search'];
    for(let i=0;i<ids.length;i++){
        let plotnum = document.getElementById(ids[i]).value;
        if(plotnum=='1'){
            if(i==0){
                get_plot1D_CS();
            }else if(i==1){
                get_plot2D_PD();
            }else if(i==2){
                get_plot2D_FD();
            }else{
                get_plot1D_CW();
            };
        }else if(plotnum==2){
            show_cavities();
        }else{
        
        }
    };
};

function show_content(but_id,content_id){
    let content_value = document.getElementById(but_id).value;
    if(content_value=="0"){
        document.getElementById(but_id).setAttribute('value',"1");
        document.getElementById(content_id).style.display='block';
        window.location.hash = "#"+content_id;
    }else{
        window.location.hash = "#"+content_id;
    };
};

//重置量測參數
function reset_paras(where){
    document.getElementById('Freqrange-'+where).innerHTML = '';
    document.getElementById('Powrange-'+where).innerHTML = '';
    document.getElementById('Fluxrange-'+where).innerHTML = '';
    document.getElementById('IFBW-'+where).innerHTML = '';
    document.getElementById('XYFreqrange-'+where).innerHTML = '';
    document.getElementById('XYPowrange-'+where).innerHTML = '';
};

function reset_address(){
    history.pushState("", document.title, window.location.pathname);
    history.go(0);
};

//-----------------Measurement settings-------------------
//start auto measurement
var MS_process = document.getElementById("Start-measure-but");
MS_process.addEventListener('click' , start_measure);
//hash to the MS window
var showcontent_MS = document.getElementById("showcontent-MS");
showcontent_MS.addEventListener('click' , show_content_MS);
//refresh all the html

var refresh= document.getElementById("refresh");
refresh.addEventListener('click' , reset_address);

// results container
var CS_overview = {}
var cavities = {};
var cavity_keys = [];
var cavities_plot = {};
var pd_powers = {};
var pd_array = {};
var flux = {};
var fd_array = {};
var q_freq = {};
var Ec = {}
var acStark = {}
var q_plot = {};
var jobid = {}

// measurement settings
var designed_num = '0';
var dc_ch = '1';
var port = 'S21,';

function start_measure(){

    dc_ch = document.getElementById('dc-channel-inp').value;
    port = document.getElementById('port-inp').value;

    // connect to autoscan1Q2js.py
    console.log("Start Measurement by Bot ")
    $.getJSON( '/autoscan1Q2js/measurement',{  
        dc_channel: JSON.stringify(dc_ch),
        inout_port: JSON.stringify(port), 
    }, function (datas) {   //need to check this is correct or not
        console.log( "Searching Finished " );
    });
    // ToSolve: How to show the results on the html?
};



function show_results(){
    let resultsBycavity = {}
    $.getJSON( '/autoscan1Q2js/get_results',{  
    }, function (results){             
        let cavity_key = results['CS']['answer'];
        for (let i=0;i<cavity_key.length;i++){   
            resultsBycavity[cavity_key[i]] = {"PowerDepnd":results["PD"][cavity_key[i]],"FluxDepnd":resuts["FD"][cavity_key[i]],"QubitSearch":resuts["CW"][cavity_key[i]]};    
        };
    });
    document.getElementById('result').innerHTML = resultsBycavity;
};

function show_content_MS(){
    window.location.hash = "#MS-content";
};

//---------------------Search JOBID--------------------------

var search_process = document.getElementById("search-jobid");
search_process.addEventListener('click' , search_jobids);

var CS_jobid = 0;
var PD_jobids = {};
var FD_jobids = {};
var CW_jobids = {};


function search_jobids(){
    $.getJSON( '/autoscan1Q2js/get_jobid',{  
    }, function (JOBIDs){
        CS_jobid = JOBIDs['CavitySearch']
        PD_jobids = JOBIDs['PowerDepend']
        FD_jobids = JOBIDs['FluxDepend']
        CW_jobids = JOBIDs['QubitSearch'] 
    });
    genopt (PD_jobids); 
};


//-----------------CavitySearch---------------------------
// 畫出baseline
var fig_CS = document.getElementById("CS-search");
fig_CS.addEventListener('click' , get_plot1D_CS);
//根據選項畫出cavities
var cavities_CS = document.getElementById("looks-CS");
cavities_CS.addEventListener('click' , show_cavities);
// 顯示量測參數
var showpara_CS = document.getElementById("sp-CS");
showpara_CS.addEventListener('click' , function(){show_paras("CS");});

//顯示內文
var showcontent_CS = document.getElementById("showcontent-CS");
showcontent_CS.addEventListener('click' , function(){show_content("showcontent-CS","CS-content");});


// generate the options in the select id
function generate_options(id,data,cata){
    // get the selector in the body
      let CavitySelect = document.getElementById(id); 
      let result_keys =  Object.keys(data)
      const opt_num = Object.keys(data).length

    // generate the options in the select
      for(let ipt=0; ipt<opt_num; ipt++){
          let option = document.createElement("option");
          option.innerHTML = result_keys[ipt];
          option.setAttribute('value',cata+result_keys[ipt]);//value = CS-5487 MHz
          CavitySelect.appendChild(option);
        };
};


// after we have the cavities, generate the correspond options in the next steps which needs to select the cavity.
function genopt (data) {
    let selectors = ['cavity-select-CS','cavity-select-PD','cavity-select-FD','cavity-select-CW']
    let catagories = ['CS-','PD-','FD-','CW-']
    const detected_num = Object.keys(data).length;
    if(detected_num>0){

        for(let i=0;i<selectors.length;i++){
            document.getElementById(selectors[i]).options.length = 0; //清除舊options
            generate_options(selectors[i],data,catagories[i]);
        };
        const result = Object.keys(data);
        document.getElementById('resultId-CS').innerHTML = 'Cavity @ : '+result;
    }else{
        alert("WARNING!!\nNo cavity is detected!");
    };   
};


// plot search result
function plot1D_2y_CS ( data, axisKeys, plotId, modenum ){
   
    let groupNumber = axisKeys.x.length;
    let color_list= []
    let tracies = [];
    let ix;
    let yGroup = ["y","y2"];
    if(modenum=='0'){
        color_list=['#1f77b4','rgb(220 20 60)'];
    }else{
        color_list=['rgb(255,255,0)','rgb(255,0,255)'];
    };

    if(modenum=='0'){
        var layout = {
            plot_bgcolor:"rgb(252, 243, 223)",
            paper_bgcolor:'rgb(252, 243, 223)',
            title:{
                text:'Scan-Results',
                font:{
                    size:30
                }
            },
            xaxis:{
                title: {
                    text:'Frequency (GHz)',
                    font:{size:25}
                },
                tickfont:{size:25},
                zeroline: false,
                color:'rgb(0,0,0)'
            },
            yaxis: {
                title: {
                    text:'Amplitude (dBm)',
                    font:{size:25},  
                },
                zeroline: false,
                color: '#1f77b4'
            },
            yaxis2: {
                title: {
                    text:'UPhase',
                    font:{size:25}
                },
                zeroline: false,
                color: 'rgb(220 20 60)',
                overlaying:'y',
                side: 'right'
            },
            showlegend: true,
            hoverlabel:{font:{size:26}}
        };
    }else{
        var layout = {
            plot_bgcolor:"black",
            paper_bgcolor:'rgb(0,0,0)',
            title:{
                text:'Scan-Results',
                font:{
                    size:30,
                    color:'rgb(0,255,255)'
                }
            },
            xaxis:{
                title: {
                    text:'Frequency (GHz)',
                    font:{size:25}
                },
                zeroline: false,
                tickfont:{size:25},
                color: 'rgb(0,255,0)',
            },
            yaxis: {
                title: {
                    text:'Amplitude (dBm)',
                    font:{size:25},  
                },
                zeroline: false,
                color: 'rgb(255,255,0)',
            },
            yaxis2: {
                title: {
                    text:'UPhase',
                    font:{size:25}
                },
                color: 'rgb(255,0,255)',
                zeroline: false,
                overlaying:'y',
                side: 'right'
            },
            showlegend: true,
            legend:{font:{color:'rgb(0,255,0)'}},
            hoverlabel:{font:{size:26}}

        };
    }; 
    
    for ( gi=0; gi<groupNumber; gi++ ){
        let xKeysInGroup = axisKeys.x[gi];
        let yKeysInGroup = axisKeys.y[gi];

        let yNumberInGroup = yKeysInGroup.length;

        for (let i = 0; i < yNumberInGroup; i++){
            
            if ( xKeysInGroup.length != 1 ){
                ix = i
            }else{
                ix = 0
            };
            let newTrace = {
                x: data[axisKeys.x[gi][ix]],
                y: data[axisKeys.y[gi][i]],
                yaxis: yGroup[gi],
                name:String(yKeysInGroup), 
                mode: 'lines',
                line:{color:color_list[gi]}
            };
                
            tracies.push(newTrace);
        
        };
    };
    Plotly.newPlot(plotId, tracies, layout);
};

var CS_overview = {};
var cavities_plot = {};
// plot the result of whole cavity 
function get_plot1D_CS(){
    let modenum = document.getElementById('dmbutton').value;  // get darkmode or not
    
    const location_id = "CavitySearch-result-plot";
    let ampPhaseKeys = {
        x: [ ["Frequency"], ["Frequency"] ] ,
        y: [ ["Amplitude"],["UPhase"] ],
    };
    let where = "CS";
    $.getJSON( '/autoscan1Q2js/plot_result',{  
        measurement_catagories : JSON.stringify(where),
        specific_jobid : JSON.stringify(CS_jobid)

    }, function (plot_items) {   //need to check this is correct or not
        cavities_plot = plot_items['plot_items']
        CS_overview = plot_items['overview']
    });

    plot1D_2y_CS(CS_overview, ampPhaseKeys, location_id,modenum);
    document.getElementById(location_id).style.display = "block";
    document.getElementById('CS-search').setAttribute('value','1');
};


// jump to cavities plot html
function show_cavities(){
    let modenum = document.getElementById('dmbutton').value;
    let cavity = document.getElementById('cavity-select-CS').value.slice(3);
    let ampPhaseKeys = {
        x: [ ["Frequency"], ["Frequency"] ] ,
        y: [ ["Amplitude"],["UPhase"] ]
    };

    let where = "CS";
    $.getJSON( '/autoscan1Q2js/plot_result',{  
        measurement_catagories:JSON.stringify(where),
        specific_jobid : JSON.stringify(CS_jobid)
    }, function (plot_items) {   //need to check this is correct or not
        cavities_plot = plot_items['plot_items']
        CS_overview = plot_items['overview']
    });

    plot1D_2y_CS(cavities_plot[cavity], ampPhaseKeys, "CavitySearch-result-plot", modenum);
    document.getElementById("CavitySearch-result-plot").style.display = "block";
    document.getElementById('CS-search').setAttribute('value','2');
};

//------------------PowerDependence-----------------------------------
// 畫出baseline
var fig_PD = document.getElementById("PD-search");
fig_PD.addEventListener('click' , get_plot2D_PD);
var showpara_PD = document.getElementById("sp-PD");
showpara_PD.addEventListener('click' , function(){show_paras("PD");});
var showcontent_PD = document.getElementById("showcontent-PD");
showcontent_PD.addEventListener('click' , function(){show_content("showcontent-PD","PD-content");});


function plot2D_PD( data,data_scatter, axisKeys,axisKeys_scatter, plotId, modenum ) {

    let paper = ''
    let color_x = ''
    let color_y = ''
    let color_z = ''
    let color_t = ''
    if(modenum=='0'){
        paper = "rgb(252, 243, 223)";
        color_x = "rgb(0,0,0)";
        color_y = "rgb(0,0,0)";
        color_z = "rgb(0,0,0)";
        color_t = 'rgb(0,0,0)';
    }else{
        paper = "rgb(0,0,0)";
        color_x = "rgb(0,255,0)";
        color_y = 'rgb(255,255,0)';
        color_z = 'rgb(255,0,255)'
        color_t = 'rgb(0,255,255)';
    };
    // Frame assembly:
    var trace = {
        z: data[axisKeys.z], 
        x: data[axisKeys.x], 
        y: data[axisKeys.y], 
        zsmooth: 'best',
        mode: 'lines', 
        type: 'heatmap',
        width: 2.5,
        colorbar:{
            tickfont:{color:color_z,size:25},
            title:{
                text:'Amplitude (dBm)',
                side:'right',
                font:{size:30,color:color_z}
            }
        },
    };
    var trace_scatter = { 
        x: data_scatter[axisKeys_scatter.x], 
        y: data_scatter[axisKeys_scatter.y],
        mode:'markers',
        name:"Fr",
        line:{color:'#37A22F'}
    };
    var layout = {
        paper_bgcolor:paper,
        title:{
            text:'PowerDependence-Results',
            font:{
                size:30,
                color:color_t
            }
        },
        xaxis:{
            title: {
                text:'Power (dBm)',
                font:{size:25}
            },
            zeroline: false,
            color:color_x,
            tickfont:{size:25},
        },
        yaxis: {
            title: {
                text:'Frequency (GHz)',
                font:{size:25},  
            },
            tickfont:{size:25},
            color: color_y
        },
        yaxis2: {
            
        },
        showlegend: false,
        hoverlabel:{font:{size:26}}
    };
    var Trace = [trace,trace_scatter]
    Plotly.newPlot(plotId, Trace,layout);
};



var pd_plot = {};
function get_plot2D_PD(){
    let modenum = document.getElementById('dmbutton').value;  //darkmode or not
    let cavity = document.getElementById('cavity-select-PD').value.slice(3);
    const location_id = "PowerDep-result-plot";
    // check the column name of the dataframe
    let PDKeys = {
        x: [ "Power" ] ,
        y: [ "Frequency" ],
        z: [ "Amplitude" ]
    };
    let PDKeys_scatter = {
        x: [ "Power" ] ,
        y: [ "Fr" ],
    }

    let where = "PD";
    $.getJSON( '/autoscan1Q2js/plot_result',{  
        measurement_catagories:JSON.stringify(where),
        specific_jobid : JSON.stringify(PD_jobids[cavity]),
        target_cavity : JSON.stringify(cavity)
    }, function (plot_items) {   //need to check this is correct or not
        pd_plot = plot_items;
    });

    //make up the quantification output

    plot2D_PD(pd_plot['3D_axis'], pd_plot['scatter'], PDKeys, PDKeys_scatter, location_id,modenum);
    document.getElementById(location_id).style.display = "block";
    document.getElementById('PD-search').setAttribute('value','1');

};

//-------------------FluxDependence---------------------------------
// 畫出baseline
var fig_FD = document.getElementById("FD-search");
fig_FD.addEventListener('click' , get_plot2D_FD);
var showpara_FD = document.getElementById("sp-FD");
showpara_FD.addEventListener('click' , function(){show_paras("FD");});
var showcontent_FD = document.getElementById("showcontent-FD");
showcontent_FD.addEventListener('click' , function(){show_content("showcontent-FD","FD-content");});



function plot2D_FD( data,data_scatter, axisKeys,axisKeys_scatter, plotId, modenum ) {

    let paper = ''
    let color_x = ''
    let color_y = ''
    let color_z = ''
    let color_t = ''
    if(modenum=='0'){
        paper = "rgb(252, 243, 223)";
        color_x = "rgb(0,0,0)";
        color_y = "rgb(0,0,0)";
        color_z = "rgb(0,0,0)";
        color_t = 'rgb(0,0,0)';
    }else{
        paper = "rgb(0,0,0)";
        color_x = "rgb(0,255,0)";
        color_y = 'rgb(255,255,0)';
        color_z = 'rgb(255,0,255)'
        color_t = 'rgb(0,255,255)';
    };
    // Frame assembly:
    var trace = {
        z: data[axisKeys.z], 
        x: data[axisKeys.x], 
        y: data[axisKeys.y], 
        zsmooth: 'best',
        mode: 'lines', 
        type: 'heatmap',
        width: 2.5,
        colorbar:{
            tickfont:{color:color_z,size:25},
            title:{
                text:'Amplitude (dBm)',
                side:'right',
                font:{size:30,color:color_z}
            }
        },
    };
    var trace_scatter = { 
        x: data_scatter[axisKeys_scatter.x], 
        y: data_scatter[axisKeys_scatter.y],
        mode:'markers',
        name:"Fr",
        line:{color:'#37A22F'}
    };
    var layout = {
        paper_bgcolor:paper,
        title:{
            text:'PowerDependence-Results',
            font:{
                size:30,
                color:color_t
            }
        },
        xaxis:{
            title: {
                text:'Flux (µA)',
                font:{size:25}
            },
            zeroline: false,
            color:color_x,
            tickfont:{size:25},
        },
        yaxis: {
            title: {
                text:'Frequency (GHz)',
                font:{size:25},  
            },
            tickfont:{size:25},
            color: color_y
        },
        yaxis2:{},
        showlegend: false,
        hoverlabel:{font:{size:26}}
    };
    var Trace = [trace,trace_scatter]
    Plotly.newPlot(plotId, Trace,layout);
};



var fd_plot = {};
function get_plot2D_FD(){
    let modenum = document.getElementById('dmbutton').value;  //darkmode or not
    let cavity = document.getElementById('cavity-select-FD').value.slice(3);
    const location_id = "FluxDep-result-plot";
    
    let FDKeys = {
        x: [ "Flux" ] ,
        y: [ "Frequency" ],
        z: [ "Amplitude" ]
    };
    let FDKeys_scatter = {
        x: [ "Flux" ] ,
        y: [ "Fr" ],
    };
    let where = "PD";
    $.getJSON( '/autoscan1Q2js/plot_result',{  
        measurement_catagories:JSON.stringify(where),
        specific_jobid : JSON.stringify(FD_jobids[cavity]),
        target_cavity : JSON.stringify(cavity)
    }, function (plot_items) {   //need to check this is correct or not
        fd_plot = plot_items;
    });
    
    plot2D_FD(fd_plot['3D_axis'], fd_plot['scatter'], FDKeys, FDKeys_scatter, location_id,modenum);
    document.getElementById(location_id).style.display = "block";
    document.getElementById('FD-search').setAttribute('value','1');

};


//-------------------------CWsweep-------------------------------------------
var fig_cw = document.getElementById("CW-search");
fig_cw.addEventListener('click' , get_plot1D_CW);
var showpara_CW = document.getElementById("sp-CW");
showpara_CW.addEventListener('click' , function(){show_paras("CW");});
//顯示內文
var showcontent_CW = document.getElementById("showcontent-CW");
showcontent_CW.addEventListener('click' , function(){show_content("showcontent-CW","CW-content");});
// 生成初始xypower選項
var showcontent_CW = document.getElementById("showcontent-CW");
showcontent_CW.addEventListener('click' , function(){xypowa_options_generator(mode='initialize');});
// 改變xypower選項
var xypower_switcher = document.getElementById("cavity-select-CW");
xypower_switcher.addEventListener('change' , function(){xypowa_options_generator(mode='switch');});


function plot1D_2y_CW ( data, axisKeys, plotId, modenum ){
    let groupNumber = axisKeys.x.length;
    let color_list= []
    let tracies = [];
    let ix;

    if(modenum=='0'){
        color_list=['#1f77b4','rgb(220 20 60)'];
    }else{
        color_list=['rgb(255,0,255)','rgb(255,255,0)'];
    };

    if(modenum=='0'){
        var layout = {
            plot_bgcolor:"rgb(252, 243, 223)",
            paper_bgcolor:'rgb(252, 243, 223)',
            title:{
                text:'CWsweep-Results',
                font:{
                    size:30
                }
            },
            xaxis:{
                title: {
                    text:'XY-Frequency (GHz)',
                    font:{size:25}
                },
                tickfont:{size:25},
                zeroline: false,
                color:'rgb(0,0,0)'
            },
            yaxis: {
                title: {
                    text:'Amplitude-Redefined (dBm)',
                    font:{size:25},  
                },
                color: '#1f77b4'
            },
            showlegend: true,
            hoverlabel:{font:{size:26}}
        };
    }else{
        var layout = {
            title:{
                text:'CWsweep-Results',
                font:{
                    size:30,
                    color:'rgb(0,255,255)'
                }
            },
            plot_bgcolor:"black",
            paper_bgcolor:'rgb(0,0,0)',
            xaxis:{
                title: {
                    text:'XY-Frequency (GHz)',
                    font:{size:25}
                },
                zeroline: false,
                tickfont:{size:25},
                color: 'rgb(0,255,0)',
            },
            yaxis: {
                title: {
                    text:'Amplitude-Redefined (dBm)',
                    font:{size:25},  
                },
                color: 'rgb(255,0,255)',
            },
            showlegend: true,
            legend:{font:{color:'rgb(0,255,0)'}},
            hoverlabel:{font:{size:26}}
        };
    }; 
    
    for ( gi=0; gi<groupNumber; gi++ ){
        let xKeysInGroup = axisKeys.x[gi];
        let yKeysInGroup = axisKeys.y[gi];

        let yNumberInGroup = yKeysInGroup.length;
    
        if(gi == 0){
            for (let i = 0; i < yNumberInGroup; i++){
            
                if ( xKeysInGroup.length != 1 ){
                    ix = i
                }else{
                    ix = 0
                };
                let newTrace = {
                    x: data[axisKeys.x[gi][ix]],
                    y: data[axisKeys.y[gi][i]],
                    name:String(yKeysInGroup), 
                    mode: 'lines',
                    line:{color:color_list[gi]}
                };
                    
                tracies.push(newTrace);
            
            };

        }else{
            for (let i = 0; i < yNumberInGroup; i++){
            
                if ( xKeysInGroup.length != 1 ){
                    ix = i
                }else{
                    ix = 0
                };
                let newTrace = {
                    x: data[axisKeys.x[gi][ix]],
                    y: data[axisKeys.y[gi][i]],
                    name:String(yKeysInGroup), 
                    mode: 'markers',
                    marker:{
                        color:color_list[gi],
                        symbol:'x',
                        size:14
                    }
                };
                    
                tracies.push(newTrace);
            };
        };
    };
    Plotly.newPlot(plotId, tracies, layout);
};

var q_plot = {};
function get_plot1D_CW(){
    let modenum = document.getElementById('dmbutton').value;  //darkmode or not
    const location_id = "CWsweep-result-plot";
    let cavity = document.getElementById('cavity-select-CW').value.slice(3)
    let xy_powa = document.getElementById('power-select-CW').value.slice(8)

    let CWKeys = {
        x: [ ["Sub_Frequency"], ["Targets_Freq"] ] ,
        y: [ ["Substrate_value"],["Targets_value"] ]
    };

    let where = "CW";
    $.getJSON( '/autoscan1Q2js/plot_result',{  
        measurement_catagories:JSON.stringify(where),
        specific_jobid : JSON.stringify(CW_jobids[cavity]),
        target_cavity : JSON.stringify(cavity)

    }, function (plot_items) {   //need to check this is correct or not
        q_plot = plot_items;
    });

    plot1D_2y_CW(q_plot[xy_powa], CWKeys, location_id,modenum);
    document.getElementById(location_id).style.display = "block";
    document.getElementById('CW-search').setAttribute('value','1');

};

function xypowa_options_generator(mode){
    
    // get the selector in the body
    let xyPowaSelect = document.getElementById('power-select-CW'); 
    let cavity = document.getElementById('cavity-select-CW').value.slice(3);
    let xy_options = {}


    let where = "CW";
    $.getJSON( '/autoscan1Q2js/plot_result',{  
        measurement_catagories:JSON.stringify(where),
        specific_jobid : JSON.stringify(CW_jobids[cavity]),
        target_cavity : JSON.stringify(cavity)

    }, function (plot_items) {   //need to check this is correct or not
        xy_options = Object.keys(plot_items);
    });

    const opt_num = xy_options.length
    if (mode=='initialize'){
        for(let ipt=0; ipt<opt_num; ipt++){
            let option = document.createElement("option");
            option.innerHTML = result_keys[ipt]+" dBm";
            option.setAttribute('value',"xyPower="+result_keys[ipt]);//value = "xyPower=-10"
            xyPowaSelect.appendChild(option);
        };
    }else{
        while (xyPowaSelect.options.length > 0) {
            select.remove(0);
        }
        for(let ipt=0; ipt<opt_num; ipt++){
            let option = document.createElement("option");
            option.innerHTML = result_keys[ipt]+" dBm";
            option.setAttribute('value',"xyPower="+result_keys[ipt]);//value = "xyPower=-10"
            xyPowaSelect.appendChild(option);
        };
    };
};


//---------------------------------------------------------------------------mission complete








// 顯示目前量測參數
function paras_layout(where,paras_dict){
    let paranum = document.getElementById('sp-'+where).value;
    if(where != 'CW'){
        paras_dict['XY-Frequency'] = "OPT"
        paras_dict['XY-Power'] = "OPT"
    };

    if(paranum=='1'){
        reset_paras(where);
        document.getElementById('sp-'+where).setAttribute('value','0');
    }else{
        //Show parameters
        document.getElementById('Freqrange-'+where).innerHTML = '•Frequence : '+ document.getElementById('cavity-select-'+where).value.slice(3);
        document.getElementById('Powrange-'+where).innerHTML = '•Power : '+ String(paras_dict['Power'])+' dBm';
        document.getElementById('Fluxrange-'+where).innerHTML = '•Flux : '+ String(paras_dict['Flux-Bias']);
        document.getElementById('IFBW-'+where).innerHTML = '•IF Bandwidth : '+ String(paras_dict['IF-Bandwidth']);
        document.getElementById('XYFreqrange-'+where).innerHTML = '•XY-Frequency Range : '+ String(paras_dict['XY-Frequency']);
        document.getElementById('XYPowrange-'+where).innerHTML = '•XY-Power : '+ String(paras_dict['XY-Power'])+' dBm';
        document.getElementById('sp-'+where).setAttribute('value','1');
    };
};



// developing... show measurement parameters
function show_paras(where){
    console.log("Access measurement parameters...")
    let step_key = ''
    let cavity_key = ''
    let request_jobid = ''
    if(where == 'CS'){
        step_key = 'CavitySearch'
        request_jobid = String(CS_jobid);

    }else if(where == 'PD'){
        step_key = 'PowerDepend'
        cavity_key = document.getElementById('cavity-select-PD').value.slice(3)
        request_jobid = String(PD_jobids[cavity_key]);
        
    }else if(where == 'FD'){
        step_key = 'FluxDepend'
        cavity_key = document.getElementById('cavity-select-FD').value.slice(3)
        request_jobid = String(FD_jobids[cavity_key]);
    }else{
        step_key = 'QubitSearch'
        cavity_key = document.getElementById('cavity-select-CW').value.slice(3)
        request_jobid = String(CW_jobids[cavity_key]);
    };

    $.getJSON( '/autoscan1Q2js/measurement_paras',{  
        this_jobid: JSON.stringify(request_id),
    }, function (paras){
        paras_layout(where,paras)
    });
};