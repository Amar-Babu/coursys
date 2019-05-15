/*
This is added specifically for the CMPT internal transfer application form, so that the CGPA can be calculated
automagically by the system.

This is extremely unrobust, as it depends on the IDs of the dropdowns and output not changing.  Obviously, since this
is all client-side, a clever student can also use the console to simply change the value manually.  Not much we can do
about that.  People receiving this form will have to be vigilant.
 */

$(document).ready(function() {
    var output = $("#id_10");
    // First thing to do is to disable this input to stop students from changing it.
    output.prop("readonly", true);
    // Every time we change a dropdown, disable duplicates in CMPT cousres and recalculate the CRGPA
    $("select").change(function () {
        disableDuplicates();
        calculateCRGPA();
    });
    // Disable duplicates the first time we load.
    disableDuplicates()
    // After we disabled duplicates the first time, take the second drop down and set its value to the first
    // non-disabled selection.
    $('#id_6').find('option:enabled:first').prop('selected',true);
    // Disable duplicates once more so the one selected in for the second dropdown in the last step is disabled in the first dropdown.
    disableDuplicates();
    // Finally, calculate the CRGPA after making these changes the first time we load.  After that, the change handler
    // should take care of this.
    calculateCRGPA();
});


/* All courses except these 2 are 3 credits. */
function getCredits(selector) {
    switch (selector.children(":selected").text().toUpperCase()) {
        case "CMPT 275":
            return 4;
        case "MATH 150":
            return 4;
        default:
            return 3;
    }
}

/* The value is already in the drop down, just make sure it"s a float. */
function getGPAValue(selector) {
    return parseFloat(selector.val());
}

function checkEquivalency(val) {
    // In addition to duplicates, some courses are considered equivalent.  If you select one in one dropdown, you
    // should not be able to select any equivalents in the other.

    switch (val) {
        case "CMPT 125":
        case "CMPT 128":
        case "CMPT 129":
        case "CMPT 135":
        case "ENSC 251 AND ENSC 252":
            return "CMPT 125";
        case "CMPT 275":
        case "CMPT 276":
            return "CMPT 275";
        case "CMPT 295":
        case "CMPT 150/ENSC 150":
        case "CMPT 250/ENSC 250":
            return "CMPT 150";
        default:
            return val;
    }
}

function disableDuplicates() {
    // Some CMPT courses are in both the dropdowns.  Every time we change the values, make sure the duplicates are
    // disabled.

    // Re-enable every option...
    $("#id_4 option").removeAttr("disabled");
    // Then find the one that is selected in the other drop-down and disabled that.
    $("#id_4 option").filter(function() {
        return checkEquivalency($(this).text().trim()) == checkEquivalency($('#id_6').children(":selected").text().trim());}).attr('disabled','disabled');
    // Lather, rinse, repeat for the other one.
    $("#id_6 option").removeAttr("disabled");
    $("#id_6 option").filter(function() {
        return checkEquivalency($(this).text().trim()) == checkEquivalency($('#id_4').children(":selected").text().trim());}).attr('disabled','disabled');
}


function calculateCRGPA() {
    var courseInputs = [$("#id_4"), $("#id_6"), $("#id_8")];
    var gradeInputs = [$("#id_5"), $("#id_7"), $("#id_9")];
    var output = $("#id_10");
    var totalCredits = 0;
    var totalGP = 0.00;
    for (var i = 0; i < courseInputs.length; i++)
    {
        var credits = getCredits(courseInputs[i]);
        var gpa = getGPAValue(gradeInputs[i]);
        totalCredits += credits;
        totalGP += credits * gpa;
    }
    var CGPA = totalGP / totalCredits;
    output.val(CGPA.toFixed(2));
}
